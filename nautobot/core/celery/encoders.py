import logging
from zoneinfo import ZoneInfo

from rest_framework.utils.encoders import JSONEncoder

logger = logging.getLogger(__name__)


class NautobotKombuJSONEncoder(JSONEncoder):
    """
    Custom JSON encoder based on restframework's JSONEncoder that knows how to encode certain classes.
    This is useful in passing special objects to and from Celery tasks.
    """

    def default(self, obj):
        if isinstance(obj, set):
            # Convert a set to a list for passing to and from a task
            return list(obj)
        elif isinstance(obj, Exception):
            # JobResult.result uses NautobotKombuJSONEncoder as an encoder and expects a JSONSerializable object,
            # although an exception, such as a RuntimeException, can be supplied as the obj.
            return f"{obj.__class__.__name__}: {obj}"
        elif isinstance(obj, ZoneInfo):
            return obj.key
        else:
            return super().default(obj)
