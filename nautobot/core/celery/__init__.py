import json
import logging
import os
from pathlib import Path
import shutil
import sys

from celery import Celery, shared_task, signals
from celery.app.log import TaskFormatter
from celery.utils.log import get_logger
from django.apps import apps
from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from django.utils.functional import SimpleLazyObject
from django.utils.module_loading import import_string
from kombu.serialization import register
from prometheus_client import CollectorRegistry, multiprocess, start_http_server

from nautobot import add_failure_logger, add_success_logger
from nautobot.core.celery.control import discard_git_repository, refresh_git_repository  # noqa: F401  # unused-import
from nautobot.core.celery.encoders import NautobotKombuJSONEncoder
from nautobot.core.celery.log import NautobotDatabaseHandler
from nautobot.core.utils.module_loading import import_modules_privately
from nautobot.extras.plugins.utils import import_object
from nautobot.extras.registry import registry

logger = logging.getLogger(__name__)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nautobot_config")


class NautobotCelery(Celery):
    task_cls = "nautobot.core.celery.task:NautobotTask"


app = NautobotCelery("nautobot")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@signals.import_modules.connect
def import_jobs(sender=None, **kwargs):
    """
    Import system Jobs into Nautobot as well as Jobs from JOBS_ROOT and GIT_ROOT.
    Import app-provided jobs if the app provides dynamic jobs.

    Note that app-provided jobs are automatically imported at startup time via NautobotAppConfig.ready()
    """
    import nautobot.core.jobs
    import nautobot.ipam.jobs  # noqa: F401

    _import_jobs_from_jobs_root()
    _import_dynamic_jobs_from_apps()

    try:
        _import_jobs_from_git_repositories()
    except (
        OperationalError,  # Database not present, as may be the case when running pylint-nautobot
        ProgrammingError,  # Database not ready yet, as may be the case on initial startup and migration
    ):
        pass


def _import_jobs_from_jobs_root():
    """
    (Re)import all modules in settings.JOBS_ROOT.
    """
    if not (settings.JOBS_ROOT and os.path.isdir(settings.JOBS_ROOT)):
        return

    # Flush any previously loaded non-system, non-App Jobs
    for job_class_path in list(registry["jobs"]):
        if job_class_path.startswith("nautobot."):
            # System job
            continue
        if any(job_class_path.startswith(f"{app_name}.") for app_name in settings.PLUGINS):
            # App provided job
            continue
        try:
            from nautobot.extras.models import GitRepository

            if any(
                job_class_path.startswith(f"{repo.slug}.")
                for repo in GitRepository.objects.filter(provided_contents__contains="extras.job")
            ):
                # Git provided job
                continue
        except ProgrammingError:  # Database not ready yet, as may be the case on initial startup and migration
            pass
        # Else, it's presumably a JOBS_ROOT job
        del registry["jobs"][job_class_path]

    # Load all modules in JOBS_ROOT
    import_modules_privately(path=os.path.realpath(settings.JOBS_ROOT))


def _import_jobs_from_git_repositories():
    git_root = os.path.realpath(settings.GIT_ROOT)
    if not (git_root and os.path.exists(git_root)):
        return

    from nautobot.extras.models import GitRepository

    # Make sure there are no git clones in GIT_ROOT that *aren't* tracked by a GitRepository;
    # for example, maybe a GitRepository was deleted while this worker process wasn't running?
    for filename in os.listdir(git_root):
        filepath = os.path.join(git_root, filename)
        if (
            os.path.isdir(filepath)
            and os.path.isdir(os.path.join(filepath, ".git"))
            and not GitRepository.objects.filter(slug=filename).exists()
        ):
            logger.warning("Deleting unmanaged (leftover?) Git repository clone at %s", filepath)
            shutil.rmtree(filepath, ignore_errors=True)

    # Make sure all GitRepository records that include Jobs have up-to-date git clones, and load their jobs
    for repo in GitRepository.objects.filter(provided_contents__contains="extras.job"):
        refresh_git_repository(state=None, repository_pk=repo.pk, head=repo.current_head)


def _import_dynamic_jobs_from_apps():
    for app_name in settings.PLUGINS:
        app_config = apps.get_app_config(app_name)
        if not getattr(app_config, "provides_dynamic_jobs", False):
            continue

        # Unload job modules from sys.modules if they were previously loaded
        app_jobs = getattr(app_config, "features", {}).get("jobs", [])
        for job in app_jobs:
            if job.__module__ in sys.modules:
                del sys.modules[job.__module__]

        # Load app jobs
        app_config.features["jobs"] = import_object(f"{app_config.__module__}.{app_config.jobs}")


def add_nautobot_log_handler(logger_instance, log_format=None):
    """Add NautobotDatabaseHandler to logger and update logger level filtering to send all log levels to our handler."""
    if any(isinstance(h, NautobotDatabaseHandler) for h in logger_instance.handlers):
        return
    if logger_instance.level not in (logging.NOTSET, logging.DEBUG):
        for handler in logger_instance.handlers:
            handler.setLevel(logger_instance.level)
    logger_instance.setLevel(logging.DEBUG)

    if log_format is None:
        log_format = app.conf.worker_task_log_format
    handler = NautobotDatabaseHandler()
    handler.setFormatter(TaskFormatter(log_format, use_color=False))
    logger_instance.addHandler(handler)


@signals.after_setup_logger.connect
def setup_nautobot_global_logging(logger, **kwargs):  # pylint: disable=redefined-outer-name
    """Add SUCCESS and FAILURE logs to celery global logger."""
    logger.success = add_success_logger()
    logger.failure = add_failure_logger()


@signals.after_setup_task_logger.connect
def setup_nautobot_task_logging(logger, **kwargs):  # pylint: disable=redefined-outer-name
    """Add SUCCESS and FAILURE logs to celery task logger."""
    logger.success = add_success_logger()
    logger.failure = add_failure_logger()


@signals.celeryd_after_setup.connect
def setup_nautobot_job_logging(sender, instance, conf, **kwargs):
    """Add nautobot database logging handler to celery stdout/stderr redirect logger and celery task logger."""
    task_logger = get_logger("celery.task")
    add_nautobot_log_handler(task_logger)
    if conf.worker_redirect_stdouts:
        redirect_logger = get_logger("celery.redirected")
        add_nautobot_log_handler(redirect_logger)


@signals.worker_ready.connect
def setup_prometheus(**kwargs):
    """This sets up an HTTP server to serve prometheus metrics from the celery workers."""
    # Don't set up the server if the port is undefined
    if not settings.CELERY_WORKER_PROMETHEUS_PORTS:
        return

    logger.info("Setting up prometheus metrics HTTP server for celery worker.")

    # Ensure that the multiprocess coordination directory exists. Note that we explicitly don't clear this directory
    # out because the worker might share its filesystem with the core app or another worker. The multiprocess
    # mechanism from prometheus-client takes care of this.
    multiprocess_coordination_directory = Path(os.environ["prometheus_multiproc_dir"])
    multiprocess_coordination_directory.mkdir(parents=True, exist_ok=True)

    # Set up the collector registry
    collector_registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(collector_registry, path=multiprocess_coordination_directory)
    for port in settings.CELERY_WORKER_PROMETHEUS_PORTS:
        try:
            start_http_server(port, registry=collector_registry)
            break
        except OSError:
            continue
    else:
        logger.warning("Cannot export Prometheus metrics from worker, no available ports in range.")


def nautobot_kombu_json_loads_hook(data):
    """
    In concert with the NautobotKombuJSONEncoder json encoder, this object hook method decodes
    objects that implement the `__nautobot_type__` interface via the `nautobot_deserialize()` class method.
    """
    if "__nautobot_type__" in data:
        qual_name = data.pop("__nautobot_type__")
        logger.debug("Performing nautobot deserialization for type %s", qual_name)
        cls = import_string(qual_name)  # fully qualified dotted import path
        if cls:
            return SimpleLazyObject(lambda: cls.objects.get(id=data["id"]))
        else:
            raise TypeError(f"Unable to import {qual_name} during nautobot deserialization")
    else:
        return data


# Encoder function
def _dumps(obj):
    return json.dumps(obj, cls=NautobotKombuJSONEncoder, ensure_ascii=False)


# Decoder function
def _loads(obj):
    return json.loads(obj, object_hook=nautobot_kombu_json_loads_hook)


# Register the custom serialization type
register("nautobot_json", _dumps, _loads, content_type="application/x-nautobot-json", content_encoding="utf-8")


#
# nautobot_task
#
# By exposing `shared_task` within our own namespace, we leave the door open to
# extending and expanding the usage and meaning of shared_task without having
# to undergo further refactoring of task's decorators. We could also transparently
# swap out shared_task to a custom base task.
#

nautobot_task = shared_task


registry["jobs"] = {}


def register_jobs(*jobs):
    """
    Method to register jobs - with Celery in Nautobot 2.0 through 2.2.2, with Nautobot itself in 2.2.3 and later.
    """
    for job in jobs:
        if job.class_path not in registry["jobs"]:
            registry["jobs"][job.class_path] = job
