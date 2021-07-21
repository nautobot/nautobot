import collections
import hashlib
import hmac

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.deconstruct import deconstructible
from taggit.managers import _TaggableManager

from nautobot.extras.constants import EXTRAS_FEATURES
from nautobot.extras.registry import registry


def is_taggable(obj):
    """
    Return True if the instance can have Tags assigned to it; False otherwise.
    """
    if hasattr(obj, "tags"):
        if issubclass(obj.tags.__class__, _TaggableManager):
            return True
    return False


def image_upload(instance, filename):
    """
    Return a path for uploading image attchments.
    """
    path = "image-attachments/"

    # Rename the file to the provided name, if any. Attempt to preserve the file extension.
    extension = filename.rsplit(".")[-1].lower()
    if instance.name and extension in ["bmp", "gif", "jpeg", "jpg", "png"]:
        filename = ".".join([instance.name, extension])
    elif instance.name:
        filename = instance.name

    return "{}{}_{}_{}".format(path, instance.content_type.name, instance.object_id, filename)


@deconstructible
class FeatureQuery:
    """
    Helper class that delays evaluation of the registry contents for the functionality store
    until it has been populated.
    """

    def __init__(self, feature):
        self.feature = feature

    def __call__(self):
        return self.get_query()

    def get_query(self):
        """
        Given an extras feature, return a Q object for content type lookup
        """
        query = Q()
        for app_label, models in registry["model_features"][self.feature].items():
            query |= Q(app_label=app_label, model__in=models)

        return query

    def get_choices(self):
        """
        Given an extras feature, return a list of 2-tuple of `(model_label, pk)`
        suitable for use as `choices` on a choice field:

            >>> FeatureQuery('statuses').get_choices()
            [('dcim.device', 13), ('dcim.rack', 34)]
        """
        return [(f"{ct.app_label}.{ct.model}", ct.pk) for ct in ContentType.objects.filter(self.get_query())]


def extras_features(*features):
    """
    Decorator used to register extras provided features to a model
    """

    def wrapper(model_class):
        # Initialize the model_features store if not already defined
        if "model_features" not in registry:
            registry["model_features"] = {f: collections.defaultdict(list) for f in EXTRAS_FEATURES}
        for feature in features:
            if feature in EXTRAS_FEATURES:
                app_label, model_name = model_class._meta.label_lower.split(".")
                registry["model_features"][feature][app_label].append(model_name)
            else:
                raise ValueError("{} is not a valid extras feature!".format(feature))
        return model_class

    return wrapper


def generate_signature(request_body, secret):
    """
    Return a cryptographic signature that can be used to verify the authenticity of webhook data.
    """
    hmac_prep = hmac.new(key=secret.encode("utf8"), msg=request_body, digestmod=hashlib.sha512)
    return hmac_prep.hexdigest()


def get_worker_count(request):
    """
    Return a count of the active Celery workers.
    """
    # Inner imports so we don't risk circular imports
    from nautobot.core.celery import app  # noqa
    from rq.worker import Worker  # noqa
    from django_rq.queues import get_connection  # noqa

    # Try RQ first since, it's faster.
    rq_count = Worker.count(get_connection("default"))

    # Celery next, since it's slower.
    inspect = app.control.inspect()
    active = inspect.active()  # None if no active workers
    celery_count = len(active) if active is not None else 0

    if rq_count and not celery_count:
        messages.warning(request, "RQ workers are deprecated. Please migrate your workers to Celery.")

    return celery_count
