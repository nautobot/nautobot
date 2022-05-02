import collections
import hashlib
import hmac
import inspect
import logging
import pkgutil
import sys

from cacheops import file_cache
from django.apps import apps
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.deconstruct import deconstructible
from taggit.managers import _TaggableManager

from nautobot.core.fields import slugify_dots_to_dashes
from nautobot.extras.constants import (
    EXTRAS_FEATURES,
    JOB_MAX_GROUPING_LENGTH,
    JOB_MAX_NAME_LENGTH,
    JOB_MAX_SLUG_LENGTH,
    JOB_MAX_SOURCE_LENGTH,
    JOB_OVERRIDABLE_FIELDS,
)
from nautobot.extras.registry import registry


logger = logging.getLogger(__name__)


@file_cache.cached(timeout=60)
def get_job_content_type():
    """Return a cached instance of the `ContentType` for `extras.Job`."""
    return ContentType.objects.get(app_label="extras", model="job")


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
    Return a path for uploading image attachments.
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


@deconstructible
class TaggableClassesQuery:
    """
    Helper class to get ContentType models that implements tags(TaggableManager)
    """

    def list_subclasses(self):
        """
        Return a list of classes that has implements tags e.g tags = TaggableManager(...)
        """
        return [
            _class
            for _class in apps.get_models()
            if hasattr(_class, "tags") and isinstance(_class.tags, _TaggableManager)
        ]

    def __call__(self):
        """
        Given an extras feature, return a Q object for content type lookup
        """
        query = Q()
        for model in self.list_subclasses():
            query |= Q(app_label=model._meta.app_label, model=model.__name__.lower())

        return query

    @property
    def as_queryset(self):
        return ContentType.objects.filter(self()).order_by("app_label", "model")

    def get_choices(self):
        return [(f"{ct.app_label}.{ct.model}", ct.pk) for ct in self.as_queryset]


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


# namedtuple class yielded by the jobs_in_directory generator function, below
# Example: ("devices", <module "devices">, "Hostname", <class "devices.Hostname">)
JobClassInfo = collections.namedtuple("JobClassInfo", ["module_name", "module", "job_class_name", "job_class"])


def jobs_in_directory(path, module_name=None, reload_modules=True):
    """
    Walk the available Python modules in the given directory, and for each module, walk its Job class members.

    Args:
        path (str): Directory to import modules from, outside of sys.path
        module_name (str): Specific module name to select; if unspecified, all modules will be inspected
        reload_modules (bool): Whether to force reloading of modules even if previously loaded into Python.

    Yields:
        JobClassInfo: (module_name, module, job_class_name, job_class)
    """
    from .jobs import is_job  # avoid circular import

    for importer, discovered_module_name, _ in pkgutil.iter_modules([path]):
        if module_name and discovered_module_name != module_name:
            continue
        if reload_modules and discovered_module_name in sys.modules:
            del sys.modules[discovered_module_name]
        try:
            module = importer.find_module(discovered_module_name).load_module(discovered_module_name)
        except Exception as exc:
            logger.error(f"Unable to load module {module_name} from {path}: {exc}")
            # TODO: we want to be able to report these errors to the UI in some fashion?
            continue
        # Get all members of the module that are Job subclasses
        for job_class_name, job_class in inspect.getmembers(module, is_job):
            yield JobClassInfo(discovered_module_name, module, job_class_name, job_class)


def refresh_job_model_from_job_class(job_model_class, job_source, job_class, *, git_repository=None):
    """
    Create or update a job_model record based on the metadata of the provided job_class.

    Note that job_model_class is a parameter (rather than doing a "from nautobot.extras.models import Job") because
    this function may be called from various initialization processes (such as the "nautobot_database_ready" signal)
    and in that case we need to not import models ourselves.
    """
    if git_repository is not None:
        default_slug = slugify_dots_to_dashes(
            f"{job_source}-{git_repository.slug}-{job_class.__module__}-{job_class.__name__}"
        )
    else:
        default_slug = slugify_dots_to_dashes(f"{job_source}-{job_class.__module__}-{job_class.__name__}")

    # Unrecoverable errors
    if len(job_source) > JOB_MAX_SOURCE_LENGTH:  # Should NEVER happen
        logger.error(
            'Unable to store Jobs from "%s" as Job models because the source exceeds %d characters in length!',
            job_source,
            JOB_MAX_SOURCE_LENGTH,
        )
        return (None, False)
    if len(job_class.__module__) > JOB_MAX_NAME_LENGTH:
        logger.error(
            'Unable to store Jobs from module "%s" as Job models because the module exceeds %d characters in length!',
            job_class.__module__,
            JOB_MAX_NAME_LENGTH,
        )
        return (None, False)
    if len(job_class.__name__) > JOB_MAX_NAME_LENGTH:
        logger.error(
            'Unable to represent Job class "%s" as a Job model because the class name exceeds %d characters in length!',
            job_class.__name__,
            JOB_MAX_NAME_LENGTH,
        )
        return (None, False)

    # Recoverable errors
    if len(job_class.grouping) > JOB_MAX_GROUPING_LENGTH:
        logger.warning(
            'Job class "%s" grouping "%s" exceeds %d characters in length, it will be truncated in the database.',
            job_class.__name__,
            job_class.grouping,
            JOB_MAX_GROUPING_LENGTH,
        )
    if len(job_class.name) > JOB_MAX_NAME_LENGTH:
        logger.warning(
            'Job class "%s" name "%s" exceeds %d characters in length, it will be truncated in the database.',
            job_class.__name__,
            job_class.name,
            JOB_MAX_NAME_LENGTH,
        )

    job_model, created = job_model_class.objects.get_or_create(
        source=job_source[:JOB_MAX_SOURCE_LENGTH],
        git_repository=git_repository,
        module_name=job_class.__module__[:JOB_MAX_NAME_LENGTH],
        job_class_name=job_class.__name__[:JOB_MAX_NAME_LENGTH],
        defaults={
            "slug": default_slug[:JOB_MAX_SLUG_LENGTH],
            "grouping": job_class.grouping[:JOB_MAX_GROUPING_LENGTH],
            "name": job_class.name[:JOB_MAX_NAME_LENGTH],
            "installed": True,
            "enabled": False,
        },
    )

    for field_name in JOB_OVERRIDABLE_FIELDS:
        # Was this field directly inherited from the job before, or was it overridden in the database?
        if not getattr(job_model, f"{field_name}_override", False):
            # It was inherited and not overridden
            setattr(job_model, field_name, getattr(job_class, field_name))

    if not created:
        # Mark it as installed regardless
        job_model.installed = True

    job_model.save()

    logger.info(
        '%s Job "%s: %s" from <%s%s: %s>',
        "Created" if created else "Refreshed",
        job_model.grouping,
        job_model.name,
        job_source,
        f" {git_repository.name}" if git_repository is not None else "",
        job_class.__name__,
    )

    return (job_model, created)
