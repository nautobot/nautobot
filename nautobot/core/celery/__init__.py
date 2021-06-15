import json
import logging
import os

import nautobot

from celery import Celery
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.module_loading import import_string
from kombu.serialization import register

logger = logging.getLogger(__name__)

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nautobot.core.settings")

app = Celery("nautobot")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
# First, we need to call setup on the app to initialize settings
nautobot.setup()
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


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
    return json.dumps(obj, cls=NautobotKombuJSONEncoder)


# Decoder function
def _loads(obj):
    return json.loads(obj, object_hook=nautobot_kombu_json_loads_hook)


# Register the custom serialization type
register("nautobot_json", _dumps, _loads, content_type="application/x-nautobot-json", content_encoding="utf-8")
