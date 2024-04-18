from importlib import import_module
import json
import logging
import os
from pathlib import Path

from celery import Celery, shared_task, signals
from celery.app.log import TaskFormatter
from celery.utils.log import get_logger
from django.conf import settings
from django.utils.functional import SimpleLazyObject
from django.utils.module_loading import import_string
from kombu.serialization import register
from prometheus_client import CollectorRegistry, multiprocess, start_http_server

from nautobot.core.celery.control import discard_git_repository, refresh_git_repository  # noqa: F401  # unused-import
from nautobot.core.celery.encoders import NautobotKombuJSONEncoder
from nautobot.core.celery.log import NautobotDatabaseHandler

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
def import_jobs(sender=None, database_ready=True, **kwargs):
    """
    Import system Jobs into memory.

    Note that app-provided Jobs are automatically imported at startup time via NautobotAppConfig.ready(),
    and JOBS_ROOT and GitRepository Jobs are loaded on-demand only.
    """
    import_module("nautobot.core.jobs")


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


# 3.0 TODO: remove this method as no longer needed.
def register_jobs(*jobs):
    """
    Deprecated helper method to register jobs with Celery in Nautobot 2.0 through 2.2.1.

    No longer does anything but is kept for backward compatibility for now; should be removed in Nautobot 3.0.
    """
