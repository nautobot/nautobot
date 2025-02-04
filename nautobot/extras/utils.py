import collections
import contextlib
import copy
import hashlib
import hmac
import logging
import re
import sys
from typing import Optional

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.validators import ValidationError
from django.db import transaction
from django.db.models import Model, Q
from django.template.loader import get_template, TemplateDoesNotExist
from django.utils.deconstruct import deconstructible
import kubernetes.client
import redis.exceptions

from nautobot.core.choices import ColorChoices
from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.managers import TagsManager
from nautobot.core.models.utils import find_models_with_matching_fields
from nautobot.core.utils.data import is_uuid
from nautobot.extras.choices import DynamicGroupTypeChoices, JobQueueTypeChoices, ObjectChangeActionChoices
from nautobot.extras.constants import (
    CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL,
    EXTRAS_FEATURES,
    JOB_MAX_NAME_LENGTH,
    JOB_OVERRIDABLE_FIELDS,
)
from nautobot.extras.registry import registry

logger = logging.getLogger(__name__)


def get_base_template(base_template: Optional[str], model: type[Model]) -> str:
    """
    Attempt to locate the correct base template for an object detail view and related views, if one was not specified.

    Args:
        base_template (str, optional): If not None, this explicitly specified template will be preferred.
        model (Model): The model to identify a base template for, if base_template is None.

    Returns the specified `base_template`, if not `None`.
    Otherwise, if `"<app>/<model_name>.html"` exists (legacy ObjectView pattern), returns that string.
    Otherwise, if `"<app>/<model_name>_retrieve.html"` exists (as used in `NautobotUIViewSet`), returns that string.
    If all else fails, returns `"generic/object_retrieve.html"`.

    Note: before Nautobot 2.4.2, this API would default to "base.html" rather than "generic/object_retrieve.html".
    This behavior was changed to the current behavior to address issue #6550 and similar incorrect behavior.
    """
    if base_template is None:
        base_template = f"{model._meta.app_label}/{model._meta.model_name}.html"
        try:
            get_template(base_template)
        except TemplateDoesNotExist:
            base_template = f"{model._meta.app_label}/{model._meta.model_name}_retrieve.html"
            try:
                get_template(base_template)
            except TemplateDoesNotExist:
                base_template = "generic/object_retrieve.html"
    return base_template


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

    return f"{path}{instance.content_type.name}_{instance.object_id}_{filename}"


@deconstructible
class FeaturedQueryMixin:
    """Mixin class that gets a list of featured models."""

    def list_subclasses(self):
        """Return a list of classes that has implements this `name`."""
        raise NotImplementedError("list_subclasses is not implemented")

    def __call__(self):
        """
        Given an extras feature, return a Q object for content type lookup
        """
        query = Q()
        for model in self.list_subclasses():
            query |= Q(app_label=model._meta.app_label, model=model.__name__.lower())

        return query

    def as_queryset(self):
        return ContentType.objects.filter(self()).order_by("app_label", "model")

    def get_choices(self):
        return [(f"{ct.app_label}.{ct.model}", ct.pk) for ct in self.as_queryset()]


@deconstructible
class ChangeLoggedModelsQuery(FeaturedQueryMixin):
    """
    Helper class to get ContentType for models that implements the to_objectchange method for change logging.
    """

    def list_subclasses(self):
        """
        Return a list of classes that implement the to_objectchange method
        """
        return [_class for _class in apps.get_models() if hasattr(_class, "to_objectchange")]


def change_logged_models_queryset():
    """
    Cacheable function for cases where we need this queryset many times, such as when saving multiple objects.

    Cache is cleared by post_migrate signal (nautobot.extras.signals.post_migrate_clear_content_type_caches).
    """
    queryset = None
    cache_key = "nautobot.extras.utils.change_logged_models_queryset"
    with contextlib.suppress(redis.exceptions.ConnectionError):
        queryset = cache.get(cache_key)
    if queryset is None:
        queryset = ChangeLoggedModelsQuery().as_queryset()
        with contextlib.suppress(redis.exceptions.ConnectionError):
            cache.set(cache_key, queryset)
    return queryset


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

        # The `populate_model_features_registry` function is called in the `FeatureQuery().get_query` method instead of
        # `ExtrasConfig.ready` because `FeatureQuery().get_query` is called before `ExtrasConfig.ready`.
        # This is because `FeatureQuery` is a helper class used in `Forms` and `Serializers` that are called during the
        # initialization of the application, before `ExtrasConfig.ready` is called.
        # Calling `populate_model_features_registry` in `ExtrasConfig.ready` would lead to an outdated `model_features`
        # `registry` record being used by `FeatureQuery`.

        populate_model_features_registry()
        try:
            query = Q()
            if not self.as_dict():  # no registered models??
                raise KeyError
            else:
                for app_label, models in self.as_dict():
                    query |= Q(app_label=app_label, model__in=models)
        except KeyError:
            query = Q(pk__in=[])

        return query

    def as_dict(self):
        """
        Given an extras feature, return a iterable of app_label: [models] for content type lookup.

        Misnamed, as it returns an iterable of (key, value) (i.e. dict.items()) rather than an actual dict.

        Raises a KeyError if the given feature doesn't exist.
        """
        return registry["model_features"][self.feature].items()

    def get_choices(self):
        """
        Given an extras feature, return a list of 2-tuple of `(model_label, pk)`
        suitable for use as `choices` on a choice field:

            >>> FeatureQuery('statuses').get_choices()
            [('dcim.device', 13), ('dcim.rack', 34)]

        Cache is cleared by post_migrate signal (nautobot.extras.signals.post_migrate_clear_content_type_caches).
        """
        choices = None
        cache_key = f"nautobot.extras.utils.FeatureQuery.choices.{self.feature}"
        with contextlib.suppress(redis.exceptions.ConnectionError):
            choices = cache.get(cache_key)
        if choices is None:
            choices = [(f"{ct.app_label}.{ct.model}", ct.pk) for ct in ContentType.objects.filter(self.get_query())]
            with contextlib.suppress(redis.exceptions.ConnectionError):
                cache.set(cache_key, choices)
        return choices

    def list_subclasses(self):
        """
        Return a list of model classes that declare this feature.

        Cache is cleared by post_migrate signal (nautobot.extras.signals.post_migrate_clear_content_type_caches).
        """
        subclasses = None
        cache_key = f"nautobot.extras.utils.FeatureQuery.subclasses.{self.feature}"
        with contextlib.suppress(redis.exceptions.ConnectionError):
            subclasses = cache.get(cache_key)
        if subclasses is None:
            subclasses = [ct.model_class() for ct in ContentType.objects.filter(self.get_query())]
            with contextlib.suppress(redis.exceptions.ConnectionError):
                cache.set(cache_key, subclasses)
        return subclasses


@deconstructible
class TaggableClassesQuery(FeaturedQueryMixin):
    """
    Helper class to get ContentType models that implements tags(TagsField)
    """

    def list_subclasses(self):
        """
        Return a list of classes that has implements tags e.g tags = TagsField(...)
        """
        return [
            _class
            for _class in apps.get_models()
            if (
                hasattr(_class, "tags")
                and isinstance(_class.tags, TagsManager)
                and ".tests." not in _class.__module__  # avoid leakage from nautobot.core.tests.test_filters
            )
        ]


@deconstructible
class RoleModelsQuery(FeaturedQueryMixin):
    """
    Helper class to get ContentType models that implements role.
    """

    def list_subclasses(self):
        """
        Return a list of classes that implements roles e.g roles = ...
        """
        # Avoid circular imports
        from nautobot.extras.models.roles import RoleField

        model_classes = []
        for model_class in apps.get_models():
            if hasattr(model_class, "role") and isinstance(model_class._meta.get_field("role"), RoleField):
                model_classes.append(model_class)
        return model_classes


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
                raise ValueError(f"{feature} is not a valid extras feature!")
        return model_class

    return wrapper


def populate_model_features_registry(refresh=False):
    """
    Populate the registry model features with new apps.

    This function updates the registry model features.

    Behavior:
    - Defines a list of dictionaries called lookup_confs. Each dictionary contains:
        - 'feature_name': The name of the feature to be updated in the registry.
        - 'field_names': A list of names of fields that must be present in order for the model to be considered
                        a valid model_feature.
        - 'field_attributes': Optional dictionary of attributes to filter the fields by. Only model which fields match
                            all the attributes specified in the dictionary will be considered. This parameter can be
                            useful to narrow down the search for fields that match certain criteria. For example, if
                            `field_attributes` is set to {"related_model": RelationshipAssociation}, only fields with
                            a related model of RelationshipAssociation will be considered.
        - 'additional_constraints': Optional dictionary of additional `{field: value}` constraints that can be checked.
    - Looks up all the models in the installed apps.
    - For each dictionary in lookup_confs, calls lookup_by_field() function to look for all models that have
      fields with the names given in the dictionary.
    - Groups the results by app and updates the registry model features for each app.
    """
    if registry.get("populate_model_features_registry_called", False) and not refresh:
        return

    RelationshipAssociation = apps.get_model(app_label="extras", model_name="relationshipassociation")

    lookup_confs = [
        {
            "feature_name": "cloud_resource_types",
            "field_names": [],
            "additional_constraints": {"is_cloud_resource_type_model": True},
        },
        {
            "feature_name": "contacts",
            "field_names": ["associated_contacts"],
            "additional_constraints": {"is_contact_associable_model": True},
        },
        {
            "feature_name": "custom_fields",
            "field_names": ["_custom_field_data"],
        },
        {
            "feature_name": "metadata",
            "field_names": [],  # TODO: add "associated_metadata" ReverseRelation here when implemented
            "additional_constraints": {"is_metadata_associable_model": True},
        },
        {
            "feature_name": "relationships",
            "field_names": ["source_for_associations", "destination_for_associations"],
            "field_attributes": {"related_model": RelationshipAssociation},
        },
        {
            "feature_name": "saved_views",
            "field_names": [],
            "additional_constraints": {"is_saved_view_model": True},
        },
        {
            "feature_name": "dynamic_groups",
            # models using DynamicGroupMixin but not DynamicGroupsModelMixin will lack a static_group_association_set
            "field_names": [],
            "additional_constraints": {"is_dynamic_group_associable_model": True},
        },
    ]

    app_models = apps.get_models()
    for lookup_conf in lookup_confs:
        registry_items = find_models_with_matching_fields(
            app_models=app_models,
            field_names=lookup_conf["field_names"],
            field_attributes=lookup_conf.get("field_attributes"),
            additional_constraints=lookup_conf.get("additional_constraints"),
        )
        feature_name = lookup_conf["feature_name"]
        registry["model_features"][feature_name] = registry_items

    if not registry.get("populate_model_features_registry_called", False):
        registry["populate_model_features_registry_called"] = True


def generate_signature(request_body, secret):
    """
    Return a cryptographic signature that can be used to verify the authenticity of webhook data.
    """
    hmac_prep = hmac.new(key=secret.encode("utf8"), msg=request_body, digestmod=hashlib.sha512)
    return hmac_prep.hexdigest()


def get_celery_queues():
    """
    Return a dictionary of celery queues and the number of workers active on the queue in
    the form {queue_name: num_workers}
    """
    from nautobot.core.celery import app  # prevent circular import

    celery_queues = None
    with contextlib.suppress(redis.exceptions.ConnectionError):
        celery_queues = cache.get("nautobot.extras.utils.get_celery_queues")

    if celery_queues is None:
        celery_queues = {}
        celery_inspect = app.control.inspect()
        try:
            active_queues = celery_inspect.active_queues()
        except redis.exceptions.ConnectionError:
            # Celery seems to be not smart enough to auto-retry on intermittent failures, so let's do it ourselves:
            try:
                active_queues = celery_inspect.active_queues()
            except redis.exceptions.ConnectionError as err:
                logger.error("Repeated ConnectionError from Celery/Redis: %s", err)
                active_queues = None
        if active_queues is None:
            return celery_queues
        for task_queue_list in active_queues.values():
            distinct_queues = {q["name"] for q in task_queue_list}
            for queue in distinct_queues:
                celery_queues[queue] = celery_queues.get(queue, 0) + 1
        with contextlib.suppress(redis.exceptions.ConnectionError):
            cache.set("nautobot.extras.utils.get_celery_queues", celery_queues, timeout=5)

    return celery_queues


def get_worker_count(request=None, queue=None):
    """
    Return a count of the active Celery workers in a specified queue (Could be a JobQueue instance, instance pk or instance name).
    Defaults to the `CELERY_TASK_DEFAULT_QUEUE` setting.
    """
    from nautobot.extras.models import JobQueue

    celery_queues = get_celery_queues()
    if isinstance(queue, str):
        if is_uuid(queue):
            try:
                # check if the string passed in is a valid UUID
                queue = JobQueue.objects.get(pk=queue).name
            except JobQueue.DoesNotExist:
                return 0
        else:
            return celery_queues.get(queue, 0)
    elif isinstance(queue, JobQueue):
        queue = queue.name
    else:
        queue = settings.CELERY_TASK_DEFAULT_QUEUE

    return celery_queues.get(queue, 0)


def get_job_queue_worker_count(request=None, job_queue=None):
    """
    Return a count of the active Celery workers in a specified queue. Defaults to the `CELERY_TASK_DEFAULT_QUEUE` setting.
    Same as get_worker_count() method above, but job_queue is an actual JobQueue model instance.
    """
    # TODO currently this method is only retrieve celery specific queues and their respective worker counts
    # Refactor it to support retrieving kubernetes queues as well.
    celery_queues = get_celery_queues()
    if not job_queue:
        queue = settings.CELERY_TASK_DEFAULT_QUEUE
    else:
        queue = job_queue.name
    return celery_queues.get(queue, 0)


def get_job_queue(job_queue):
    """
    Search for a JobQueue instance based on the str job_queue.
    If no existing Job Queue not found, return None
    """
    from nautobot.extras.models import JobQueue

    queue = None
    if is_uuid(job_queue):
        try:
            # check if the string passed in is a valid UUID
            queue = JobQueue.objects.get(pk=job_queue)
        except JobQueue.DoesNotExist:
            queue = None
    else:
        try:
            # check if the string passed in is a valid name
            queue = JobQueue.objects.get(name=job_queue)
        except JobQueue.DoesNotExist:
            queue = None
    return queue


def task_queues_as_choices(task_queues):
    """
    Returns a list of 2-tuples for use in the form field `choices` argument. Appends
    worker count to the description.
    """
    if not task_queues:
        task_queues = [settings.CELERY_TASK_DEFAULT_QUEUE]

    choices = []
    celery_queues = get_celery_queues()
    for queue in task_queues:
        if not queue:
            worker_count = celery_queues.get(settings.CELERY_TASK_DEFAULT_QUEUE, 0)
        else:
            worker_count = celery_queues.get(queue, 0)
        description = f"{queue if queue else 'default queue'} ({worker_count} worker{'s'[:worker_count^1]})"
        choices.append((queue, description))
    return choices


def refresh_job_model_from_job_class(job_model_class, job_class, job_queue_class=None):
    """
    Create or update a job_model record based on the metadata of the provided job_class.

    Note that `job_model_class` and `job_queue_class` are parameters rather than local imports because
    this function may be called from various initialization processes (such as the "nautobot_database_ready" signal)
    and in that case we need to not import models ourselves.

    The `job_queue_class` parameter really should be required, but for some reason we decided to make this function
    part of the `nautobot.apps.utils` API surface and so we need it to stay backwards-compatible with Apps that might
    be calling the two-argument form of this function.
    """
    from nautobot.extras.jobs import (
        JobButtonReceiver,
        JobHookReceiver,
    )

    # Unrecoverable errors
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
    if issubclass(job_class, JobHookReceiver) and issubclass(job_class, JobButtonReceiver):
        logger.error(
            'Job class "%s" must not sub-class from both JobHookReceiver and JobButtonReceiver!',
            job_class.__name__,
        )
        return (None, False)

    # Recoverable errors
    if len(job_class.grouping) > CHARFIELD_MAX_LENGTH:
        logger.warning(
            'Job class "%s" grouping "%s" exceeds %d characters in length, it will be truncated in the database.',
            job_class.__name__,
            job_class.grouping,
            CHARFIELD_MAX_LENGTH,
        )
    if len(job_class.name) > JOB_MAX_NAME_LENGTH:
        logger.warning(
            'Job class "%s" name "%s" exceeds %d characters in length, it will be truncated in the database.',
            job_class.__name__,
            job_class.name,
            JOB_MAX_NAME_LENGTH,
        )

    # handle duplicate names by appending an incrementing counter to the end
    default_job_name = job_class.name[:JOB_MAX_NAME_LENGTH]
    job_name = default_job_name
    append_counter = 2
    existing_job_names = (
        job_model_class.objects.filter(name__startswith=job_name)
        .exclude(
            module_name=job_class.__module__[:JOB_MAX_NAME_LENGTH],
            job_class_name=job_class.__name__[:JOB_MAX_NAME_LENGTH],
        )
        .values_list("name", flat=True)
    )
    while job_name in existing_job_names:
        job_name_append = f" ({append_counter})"
        max_name_length = JOB_MAX_NAME_LENGTH - len(job_name_append)
        job_name = default_job_name[:max_name_length] + job_name_append
        append_counter += 1
    if job_name != default_job_name and "test" not in sys.argv:
        logger.warning(
            'Job class "%s" name "%s" is not unique, changing to "%s".',
            job_class.__name__,
            default_job_name,
            job_name,
        )

    try:
        with transaction.atomic():
            default_job_queue, _ = job_queue_class.objects.get_or_create(
                name=job_class.task_queues[0] if job_class.task_queues else settings.CELERY_TASK_DEFAULT_QUEUE,
                defaults={"queue_type": JobQueueTypeChoices.TYPE_CELERY},
            )
            job_model, created = job_model_class.objects.get_or_create(
                module_name=job_class.__module__[:JOB_MAX_NAME_LENGTH],
                job_class_name=job_class.__name__[:JOB_MAX_NAME_LENGTH],
                defaults={
                    "grouping": job_class.grouping[:CHARFIELD_MAX_LENGTH],
                    "name": job_name,
                    "is_job_hook_receiver": issubclass(job_class, JobHookReceiver),
                    "is_job_button_receiver": issubclass(job_class, JobButtonReceiver),
                    "read_only": job_class.read_only,
                    "supports_dryrun": job_class.supports_dryrun,
                    "installed": True,
                    "enabled": False,
                    "default_job_queue": default_job_queue,
                    "is_singleton": job_class.is_singleton,
                },
            )

            if job_name != default_job_name:
                job_model.name_override = True

            if created and job_model.module_name.startswith("nautobot."):
                # System jobs should be enabled by default when first created
                job_model.enabled = True

            for field_name in JOB_OVERRIDABLE_FIELDS:
                # Was this field directly inherited from the job before, or was it overridden in the database?
                if not getattr(job_model, f"{field_name}_override", False):
                    # It was inherited and not overridden
                    setattr(job_model, field_name, getattr(job_class, field_name))

            # Special case for backward compatibility
            # Note that the `job_model.task_queues` setter does NOT auto-create Celery JobQueue records;
            # this is a special case where we DO want to do so.
            if job_queue_class is not None and not job_model.job_queues_override:
                job_queues = []
                task_queues = job_class.task_queues or [settings.CELERY_TASK_DEFAULT_QUEUE]
                for task_queue in task_queues:
                    job_queue, _ = job_queue_class.objects.get_or_create(
                        name=task_queue, defaults={"queue_type": JobQueueTypeChoices.TYPE_CELERY}
                    )
                    job_queues.append(job_queue)
                job_model.job_queues.set(job_queues)

            if not created:
                # Mark it as installed regardless
                job_model.installed = True
                # Update the non-overridable flags in case they've changed in the source
                job_model.is_job_hook_receiver = issubclass(job_class, JobHookReceiver)
                job_model.is_job_button_receiver = issubclass(job_class, JobButtonReceiver)
                job_model.read_only = job_class.read_only
                job_model.supports_dryrun = job_class.supports_dryrun

            job_model.save()

    except Exception as exc:
        logger.error(
            'Exception while trying to create/update a database record for Job class "%s": %s', job_class.__name__, exc
        )
        return (None, False)

    logger.info(
        '%s Job "%s: %s" from <%s>',
        "Created" if created else "Refreshed",
        job_model.grouping,
        job_model.name,
        job_class.__name__,
    )

    return (job_model, created)


def run_kubernetes_job_and_return_job_result(job_queue, job_result, job_kwargs):
    """
    Pass the job to a kubernetes pod and execute it there.
    """
    pod_name = settings.KUBERNETES_JOB_POD_NAME
    pod_namespace = settings.KUBERNETES_JOB_POD_NAMESPACE
    pod_manifest = copy.deepcopy(settings.KUBERNETES_JOB_MANIFEST)
    pod_ssl_ca_cert = settings.KUBERNETES_SSL_CA_CERT_PATH
    pod_token = settings.KUBERNETES_TOKEN_PATH

    configuration = kubernetes.client.Configuration()
    configuration.host = settings.KUBERNETES_DEFAULT_SERVICE_ADDRESS
    configuration.ssl_ca_cert = pod_ssl_ca_cert
    with open(pod_token, "r") as token_file:
        token = token_file.read().strip()
    # configure API Key authorization: BearerToken
    configuration.api_key_prefix["authorization"] = "Bearer"
    configuration.api_key["authorization"] = token
    with kubernetes.client.ApiClient(configuration) as api_client:
        api_instance = kubernetes.client.BatchV1Api(api_client)

    job_result.task_kwargs = job_kwargs
    job_result.save()
    pod_manifest["metadata"]["name"] = "nautobot-job-" + str(job_result.pk)
    pod_manifest["spec"]["template"]["spec"]["containers"][0]["command"] = [
        "nautobot-server",
        "runjob_with_job_result",
        f"{job_result.pk}",
    ]
    job_result.log(f"Creating job pod {pod_name} in namespace {pod_namespace}")
    api_instance.create_namespaced_job(body=pod_manifest, namespace=pod_namespace)
    job_result.log(f"Reading job pod {pod_name} in namespace {pod_namespace}")
    api_instance.read_namespaced_job(name="nautobot-job-" + str(job_result.pk), namespace=pod_namespace)
    return job_result


def remove_prefix_from_cf_key(field_name):
    """
    field_name (str): f"cf_{cf.key}"

    Helper method to remove the "cf_" prefix
    """
    return field_name[3:]


def check_if_key_is_graphql_safe(model_name, key, field_name="key"):
    """
    Helper method to check if a key field is Python/GraphQL safe.
    Used in CustomField, ComputedField and Relationship models.
    """
    graphql_safe_pattern = re.compile("[_A-Za-z][_0-9A-Za-z]*")
    if not graphql_safe_pattern.fullmatch(key):
        raise ValidationError(
            {
                f"{field_name}": f"This {field_name} is not Python/GraphQL safe. Please do not start the {field_name} with a digit and do not use hyphens or whitespace"
            }
        )


def fixup_null_statuses(*, model, model_contenttype, status_model):
    """For instances of model that have an invalid NULL status field, create and use a special status_model instance."""
    instances_to_fixup = model.objects.filter(status__isnull=True)
    if instances_to_fixup.exists():
        null_status, _ = status_model.objects.get_or_create(
            name="NULL",
            defaults={
                "color": ColorChoices.COLOR_BLACK,
                "description": "Created by Nautobot to replace invalid null references",
            },
        )
        null_status.content_types.add(model_contenttype)
        updated_count = instances_to_fixup.update(status=null_status)
        print(f"    Found and fixed {updated_count} instances of {model.__name__} that had null 'status' fields.")


def fixup_dynamic_group_group_types(apps, *args, **kwargs):  # pylint: disable=redefined-outer-name
    """Set dynamic group group_type values correctly."""
    DynamicGroup = apps.get_model("extras", "DynamicGroup")
    DynamicGroupMembership = apps.get_model("extras", "DynamicGroupMembership")
    count_1 = count_2 = 0
    # See note in migration 0112 - for some reason, if we were to do the "intuitive" thing, and call
    # `DynamicGroup.objects.filter(children__isnull=False)`, we would unexpectedly get those groups for which their
    # *parent* is non-null. The below is an alternate approach that should remain correct even if that issue gets fixed.
    parent_group_names = set(DynamicGroupMembership.objects.values_list("parent_group__name", flat=True))
    parent_groups_with_wrong_type = DynamicGroup.objects.filter(name__in=parent_group_names).exclude(
        group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET
    )
    if parent_groups_with_wrong_type.exists():
        count_1 = parent_groups_with_wrong_type.update(group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET)
        print(f'\n    Found and fixed {count_1} DynamicGroup(s) that should be typed as "Group of groups".')

    filter_groups_with_wrong_type = DynamicGroup.objects.exclude(filter__exact={}).exclude(
        group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER
    )
    if filter_groups_with_wrong_type.exists():
        count_2 = filter_groups_with_wrong_type.update(group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER)
        print(f'\n    Found and fixed {count_2} DynamicGroup(s) that should be typed as "Filter-defined".')

    return count_1, count_2


def migrate_role_data(
    model_to_migrate,
    *,
    from_role_field_name,
    from_role_model=None,
    from_role_choiceset=None,
    to_role_field_name,
    to_role_model=None,
    to_role_choiceset=None,
    is_m2m_field=False,
):
    """
    Update all `model_to_migrate` with a value for `to_role_field` based on `from_role_field` values.

    Args:
        model_to_migrate (Model): Model with role fields to alter
        from_role_field_name (str): Name of the field on `model_to_migrate` to use as source data
        from_role_model (Model): If `from_role_field` is a ForeignKey or M2M field, the corresponding model for it
        from_role_choiceset (ChoiceSet): If `from_role_field` is a choices field, the corresponding ChoiceSet for it
        to_role_field_name (str): Name of the field on `model_to_migrate` to update based on the `from_role_field`
        to_role_model (Model): If `to_role_field` is a ForeignKey or M2M field, the corresponding model for it
        to_role_choiceset (ChoiceSet): If `to_role_field` is a choices field, the corresponding ChoiceSet for it
        is_m2m_field (bool): True if the role fields are both ManyToManyFields, else False
    """
    if from_role_model is not None and from_role_choiceset is not None:
        raise RuntimeError("from_role_model and from_role_choiceset are mutually exclusive")
    if from_role_model is None and from_role_choiceset is None:
        raise RuntimeError("One of from_role_model or from_role_choiceset must be specified and not None")
    if to_role_model is not None and to_role_choiceset is not None:
        raise RuntimeError("to_role_model and to_role_choiceset are mutually exclusive")
    if to_role_model is None and to_role_choiceset is None:
        raise RuntimeError("One of to_role_model or to_role_choiceset must be specified and not None")

    if from_role_model is not None:
        if to_role_model is not None:
            # Mapping "from" model instances to corresponding "to" model instances
            roles_translation_mapping = {
                # Use .filter().first(), not .get() because "to" role might not exist, especially on reverse migrations
                from_role: to_role_model.objects.filter(name=from_role.name).first()
                for from_role in from_role_model.objects.all()
            }
        else:
            # Mapping "from" model instances to corresponding "to" choices
            # We need to use `label` to look up the from_role instance, but `value` is what we set for the to_role_field
            inverted_to_role_choiceset = {label: value for value, label in to_role_choiceset.CHOICES}
            roles_translation_mapping = {
                from_role: inverted_to_role_choiceset.get(from_role.name, None)
                for from_role in from_role_model.objects.all()
            }
    else:
        if to_role_model is not None:
            # Mapping "from" choices to corresponding "to" model instances
            roles_translation_mapping = {
                # Use .filter().first(), not .get() because "to" role might not exist, especially on reverse migrations
                from_role_value: to_role_model.objects.filter(name=from_role_label).first()
                for from_role_value, from_role_label in from_role_choiceset.CHOICES
            }
        else:
            # Mapping "from" choices to corresponding "to" choices; we don't currently use this case, but it should work
            # We need to use `label` to look up the from_role instance, but `value` is what we set for the to_role_field
            inverted_to_role_choiceset = {label: value for value, label in to_role_choiceset.CHOICES}
            roles_translation_mapping = {
                from_role_value: inverted_to_role_choiceset.get(from_role_label, None)
                for from_role_value, from_role_label in from_role_choiceset.CHOICES
            }

    if not is_m2m_field:
        # Bulk updates of a single field are easy enough...
        for from_role_value, to_role_value in roles_translation_mapping.items():
            if to_role_value is not None:
                updated_count = model_to_migrate.objects.filter(**{from_role_field_name: from_role_value}).update(
                    **{to_role_field_name: to_role_value}
                )
                logger.info(
                    'Updated %d %s records to reference %s "%s"',
                    updated_count,
                    model_to_migrate._meta.label,
                    to_role_field_name,
                    to_role_value.name if to_role_model else to_role_value,
                )
    else:
        # ...but we have to update each instance's M2M field independently?
        for instance in model_to_migrate.objects.all():
            to_role_set = {
                roles_translation_mapping[from_role_value]
                for from_role_value in getattr(instance, from_role_field_name).all()
            }
            # Discard any null values
            to_role_set.discard(None)
            getattr(instance, to_role_field_name).set(to_role_set)
        logger.info(
            "Updated %d %s record %s M2M fields",
            model_to_migrate.objects.count(),
            model_to_migrate._meta.label,
            to_role_field_name,
        )


def bulk_delete_with_bulk_change_logging(qs, batch_size=1000):
    """
    Deletes objects in the provided queryset and creates ObjectChange instances in bulk to improve performance.
    For use with bulk delete views. This operation is wrapped in an atomic transaction.
    """
    from nautobot.extras.models import ObjectChange
    from nautobot.extras.signals import change_context_state

    change_context = change_context_state.get()
    if change_context is None:
        raise ValueError("Change logging must be enabled before using bulk_delete_with_bulk_change_logging")

    with transaction.atomic():
        try:
            queued_object_changes = []
            change_context.defer_object_changes = True
            for obj in qs.iterator():
                if not hasattr(obj, "to_objectchange"):
                    break
                if len(queued_object_changes) >= batch_size:
                    ObjectChange.objects.bulk_create(queued_object_changes)
                    queued_object_changes = []
                oc = obj.to_objectchange(ObjectChangeActionChoices.ACTION_DELETE)
                if oc is not None:
                    oc.user = change_context.get_user()
                    oc.user_name = oc.user.username
                    oc.request_id = change_context.change_id
                    oc.change_context = change_context.context
                    oc.change_context_detail = change_context.context_detail[:CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL]
                    queued_object_changes.append(oc)
            ObjectChange.objects.bulk_create(queued_object_changes)
            return qs.delete()
        finally:
            change_context.defer_object_changes = False
            change_context.reset_deferred_object_changes()
