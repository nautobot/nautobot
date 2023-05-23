import json
import logging
import os
from pathlib import Path
import pkgutil
import sys

from celery import Celery, shared_task, signals
from celery.app.log import TaskFormatter
from celery.fixups.django import DjangoFixup
from celery.utils.log import get_logger
from django.conf import settings
from django.utils.functional import SimpleLazyObject
from django.utils.module_loading import import_string
from kombu.serialization import register
from prometheus_client import CollectorRegistry, multiprocess, start_http_server

from nautobot.core.celery.encoders import NautobotKombuJSONEncoder
from nautobot.core.celery.log import NautobotDatabaseHandler


logger = logging.getLogger(__name__)
# The Celery documentation tells us to call setup on the app to initialize
# settings, but we will NOT be doing that because of a chicken-and-egg problem
# when bootstrapping the Django settings with `nautobot-server`.
#
# Note this would normally set the `DJANGO_SETTINGS_MODULE` environment variable
# which Celery and its workers need under the hood.The Celery docs and examples
# normally have you set it here, but because of our custom settings bootstrapping
# it is handled in the `nautobot.setup() call, and we have implemented a
# `nautobot-server celery` command to provide the correct context so this does
# NOT need to be called here.
# nautobot.setup()


class NautobotCelery(Celery):
    task_cls = "nautobot.core.celery.task:NautobotTask"

    def register_task(self, task, **options):
        """Override the default task name for job classes to allow app provided jobs to use the full module path."""
        from nautobot.extras.jobs import Job

        if issubclass(task, Job):
            task = task()
            task.name = task.registered_name

        return super().register_task(task, **options)


app = NautobotCelery("nautobot")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes. Again, this is possible
# only after calling `nautobot.setup()` which sets `DJANGO_SETTINGS_MODULE`.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Because of the chicken-and-egg Django settings bootstrapping issue,
# Celery doesn't automatically install its Django-specific patches.
# So we need to explicitly do so ourselves:
DjangoFixup(app).install()

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@signals.import_modules.connect
def import_tasks_from_jobs_root(sender, **kwargs):
    """Load jobs from JOBS_ROOT on celery workers."""
    jobs_root = settings.JOBS_ROOT
    if jobs_root and os.path.exists(jobs_root):
        if jobs_root not in sys.path:
            sys.path.append(jobs_root)
        for _, module_name, _ in pkgutil.iter_modules([jobs_root]):
            try:
                sender.loader.import_task_module(module_name)
            except Exception as exc:
                # logger.error(f"Unable to load module '{module_name}' from {jobs_root}: {exc:}")
                logger.exception(exc)


def add_nautobot_log_handler(logger, format=None):
    """Add NautobotDatabaseHandler to logger and update logger level filtering to send all log levels to our handler."""
    if any([isinstance(h, NautobotDatabaseHandler) for h in logger.handlers]):
        return
    if logger.level not in (logging.NOTSET, logging.DEBUG):
        for handler in logger.handlers:
            handler.setLevel(logger.level)
    logger.setLevel(logging.DEBUG)

    if format is None:
        format = app.conf.worker_task_log_format
    handler = NautobotDatabaseHandler()
    handler.setFormatter(TaskFormatter(format, use_color=False))
    logger.addHandler(handler)


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
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry, path=multiprocess_coordination_directory)
    for port in settings.CELERY_WORKER_PROMETHEUS_PORTS:
        try:
            start_http_server(port, registry=registry)
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


def register_jobs(*jobs):
    """Helper method to register multiple jobs."""
    for job in jobs:
        app.register_task(job)
