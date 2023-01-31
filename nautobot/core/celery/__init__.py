import json
import logging
import os
from pathlib import Path

from celery import Celery, shared_task, signals
from celery.fixups.django import DjangoFixup
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.module_loading import import_string
from kombu.serialization import register
from prometheus_client import CollectorRegistry, multiprocess, start_http_server

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

app = Celery("nautobot")

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


@signals.worker_ready.connect()
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


class NautobotKombuJSONEncoder(DjangoJSONEncoder):
    """
    Custom json encoder based on DjangoJSONEncoder that serializes objects that implement
    the `nautobot_serialize()` method via the `__nautobot_type__` interface. This is useful
    in passing special objects to and from Celery tasks.

    This pattern should generally be avoided by passing pointers to persisted objects to the
    Celery tasks and retrieving them from within the task execution. While this is always possible
    for model instances (which covers 99% of use cases), for rare instances where it does not,
    and the actual object must be passed, this pattern allows for encoding and decoding
    of such objects.

    It requires a conforming class to implement the instance method `nautobot_serialize()` which
    returns a json serializable dictionary of the object representation. The class must also implement
    the `nautobot_deserialize()` class method which takes the dictionary representation and returns
    an actual instance of the class.
    """

    def default(self, obj):
        if hasattr(obj, "nautobot_serialize"):
            cls = obj.__class__
            module = cls.__module__
            qual_name = ".".join([module, cls.__qualname__])  # fully qualified dotted import path
            logger.debug("Performing nautobot serialization on %s for type %s", obj, qual_name)
            data = {"__nautobot_type__": qual_name}
            data.update(obj.nautobot_serialize())
            return data

        elif isinstance(obj, set):
            # Convert a set to a list for passing to and from a task
            return list(obj)

        else:
            return DjangoJSONEncoder.default(self, obj)


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
            return cls.nautobot_deserialize(data)
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
