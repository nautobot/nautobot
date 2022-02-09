import collections
import hashlib
import hmac

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.deconstruct import deconstructible
from taggit.managers import _TaggableManager

from nautobot.extras.choices import ObjectChangeActionChoices
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


def get_worker_count(request=None):
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
        if request:
            messages.warning(request, "RQ workers are deprecated. Please migrate your workers to Celery.")

    return celery_count


def swap_status_id_with_status_value_and_label(obj):
    """Swap the status value in obj with a dict containing the status value and label"""
    from nautobot.extras.models import Status

    status_instance = Status.objects.get(id=obj["status"])
    obj["status"] = {"value": status_instance.slug, "label": status_instance.name}

    return obj


def get_instance_snapshot(instance, action):
    """
    Returns the snapshot(prev change, post change and its differences) of a model instance
    """
    from nautobot.extras.models import ObjectChange
    from nautobot.utilities.utils import shallow_compare_dict

    content_object_type = ContentType.objects.get_for_model(instance)
    changed_object_id = instance.id
    objectchanges = ObjectChange.objects.filter(
        changed_object_type=content_object_type, changed_object_id=changed_object_id
    ).order_by("-time")[:2]
    objectchanges_count = objectchanges.count()

    post_change = (
        swap_status_id_with_status_value_and_label(objectchanges[0].object_data)
        if action != ObjectChangeActionChoices.ACTION_DELETE and objectchanges_count > 0
        else None
    )
    prev_change = (
        swap_status_id_with_status_value_and_label(objectchanges[1].object_data)
        if action != ObjectChangeActionChoices.ACTION_CREATE and objectchanges_count > 1
        else None
    )

    if prev_change and post_change:
        diff_added = shallow_compare_dict(prev_change, post_change, exclude=["last_updated"])
        diff_removed = {x: prev_change.get(x) for x in diff_added}
    elif prev_change and not post_change:
        diff_added, diff_removed = None, prev_change
    else:
        diff_added, diff_removed = post_change, None

    return {
        "prev_change": prev_change if prev_change else None,
        "post_change": post_change if post_change else None,
        "differences": {"removed": diff_removed, "added": diff_added},
    }
