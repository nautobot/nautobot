import collections
import hashlib
import hmac
import inspect
import logging
import pkgutil
import re
import sys

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.validators import ValidationError
from django.db.models import Q
from django.template.defaultfilters import slugify
from django.template.loader import get_template, TemplateDoesNotExist
from django.utils.deconstruct import deconstructible
from taggit.managers import _TaggableManager

# 2.0 TODO: remove `is_taggable` import here; included for now for backwards compatibility with <1.4 code.
from nautobot.core.models.utils import find_models_with_matching_fields, is_taggable  # noqa: F401
from nautobot.extras.constants import (
    EXTRAS_FEATURES,
    JOB_MAX_GROUPING_LENGTH,
    JOB_MAX_NAME_LENGTH,
    JOB_MAX_SOURCE_LENGTH,
    JOB_OVERRIDABLE_FIELDS,
)
from nautobot.extras.registry import registry


logger = logging.getLogger(__name__)


def get_base_template(base_template, model):
    """
    Returns the name of the base template, if the base_template is not None
    Otherwise, default to using "<app>/<model>.html" as the base template, if it exists.
    Otherwise, check if "<app>/<model>_retrieve.html" used in `NautobotUIViewSet` exists.
    If both templates do not exist, fall back to "base.html".
    """
    if base_template is None:
        base_template = f"{model._meta.app_label}/{model._meta.model_name}.html"
        # 2.0 TODO(Hanlin): This can be removed once an object view has been established for every model.
        try:
            get_template(base_template)
        except TemplateDoesNotExist:
            base_template = f"{model._meta.app_label}/{model._meta.model_name}_retrieve.html"
            try:
                get_template(base_template)
            except TemplateDoesNotExist:
                base_template = "base.html"
    return base_template


def get_job_content_type():
    """Return a cached instance of the `ContentType` for `extras.Job`."""
    return ContentType.objects.get(app_label="extras", model="job")


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
        # As the `populate_model_features_registry` can be resource-intensive. The check the conditional check is used to
        # avoid calling the function multiple times and optimize the performance of the application.
        # TODO(timizuo): Provide a better solution for this; check https://github.com/nautobot/nautobot/pull/3360/files#r1131373797 comment.
        if not registry["model_features"].get("relationships"):
            populate_model_features_registry()
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

    def list_subclasses(self):
        """Return a list of model classes that declare this feature."""
        return [ct.model_class() for ct in ContentType.objects.filter(self.get_query())]


@deconstructible
class TaggableClassesQuery(FeaturedQueryMixin):
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
            if (
                hasattr(_class, "tags")
                and isinstance(_class.tags, _TaggableManager)
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


def populate_model_features_registry():
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
    - Looks up all the models in the installed apps.
    - For each dictionary in lookup_confs, calls lookup_by_field() function to look for all models that have fields with the names given in the dictionary.
    - Groups the results by app and updates the registry model features for each app.
    """
    RelationshipAssociation = apps.get_model(app_label="extras", model_name="relationshipassociation")

    lookup_confs = [
        {
            "feature_name": "custom_fields",
            "field_names": ["_custom_field_data"],
        },
        {
            "feature_name": "relationships",
            "field_names": ["source_for_associations", "destination_for_associations"],
            "field_attributes": {"related_model": RelationshipAssociation},
        },
    ]

    app_models = apps.get_models()
    for lookup_conf in lookup_confs:
        registry_items = find_models_with_matching_fields(
            app_models=app_models,
            field_names=lookup_conf["field_names"],
            field_attributes=lookup_conf.get("field_attributes"),
        )
        feature_name = lookup_conf["feature_name"]
        registry["model_features"][feature_name] = registry_items


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

    celery_queues = {}

    celery_inspect = app.control.inspect()
    active_queues = celery_inspect.active_queues()
    if active_queues is None:
        return celery_queues
    for task_queue_list in active_queues.values():
        distinct_queues = {q["name"] for q in task_queue_list}
        for queue in distinct_queues:
            celery_queues.setdefault(queue, 0)
            celery_queues[queue] += 1

    return celery_queues


def get_worker_count(request=None, queue=None):
    """
    Return a count of the active Celery workers in a specified queue. Defaults to the `CELERY_TASK_DEFAULT_QUEUE` setting.
    """
    celery_queues = get_celery_queues()
    if not queue:
        queue = settings.CELERY_TASK_DEFAULT_QUEUE
    return celery_queues.get(queue, 0)


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


# namedtuple class yielded by the jobs_in_directory generator function, below
# Example: ("devices", <module "devices">, "Hostname", <class "devices.Hostname">, None)
# Example: ("devices", None, None, None, "error at line 40")
JobClassInfo = collections.namedtuple(
    "JobClassInfo",
    ["module_name", "module", "job_class_name", "job_class", "error"],
    defaults=(None, None, None, None),  # all parameters except `module_name` are optional and default to None.
)


def jobs_in_directory(path, module_name=None, reload_modules=True, report_errors=False):
    """
    Walk the available Python modules in the given directory, and for each module, walk its Job class members.

    Args:
        path (str): Directory to import modules from, outside of sys.path
        module_name (str): Specific module name to select; if unspecified, all modules will be inspected
        reload_modules (bool): Whether to force reloading of modules even if previously loaded into Python.
        report_errors (bool): If True, when an error is encountered, yield a JobClassInfo with the given error.
                              If False (default), log the error but do not yield anything.

    Yields:
        JobClassInfo: (module_name, module, job_class_name, job_class, error)
    """
    from .jobs import is_job  # avoid circular import

    for importer, discovered_module_name, _ in pkgutil.iter_modules([path]):
        if module_name and discovered_module_name != module_name:
            continue
        if reload_modules and discovered_module_name in sys.modules:
            del sys.modules[discovered_module_name]
        try:
            module = importer.find_module(discovered_module_name).load_module(discovered_module_name)
            # Get all members of the module that are Job subclasses
            for job_class_name, job_class in inspect.getmembers(module, is_job):
                yield JobClassInfo(discovered_module_name, module, job_class_name, job_class)
        except Exception as exc:
            logger.error(f"Unable to load module {discovered_module_name} from {path}: {exc}")
            if report_errors:
                yield JobClassInfo(module_name=discovered_module_name, error=exc)


def refresh_job_model_from_job_class(job_model_class, job_source, job_class, *, git_repository=None):
    """
    Create or update a job_model record based on the metadata of the provided job_class.

    Note that job_model_class is a parameter (rather than doing a "from nautobot.extras.models import Job") because
    this function may be called from various initialization processes (such as the "nautobot_database_ready" signal)
    and in that case we need to not import models ourselves.
    """
    from nautobot.extras.jobs import (
        JobHookReceiver,
        JobButtonReceiver,
    )  # imported here to prevent circular import problem

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
    if issubclass(job_class, JobHookReceiver) and issubclass(job_class, JobButtonReceiver):
        logger.error(
            'Job class "%s" must not sub-class from both JobHookReceiver and JobButtonReceiver!',
            job_class.__name__,
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

    # handle duplicate names by appending an incrementing counter to the end
    default_job_name = job_class.name[:JOB_MAX_NAME_LENGTH]
    job_name = default_job_name
    append_counter = 2
    existing_job_names = (
        job_model_class.objects.filter(name__startswith=job_name)
        .exclude(
            source=job_source[:JOB_MAX_SOURCE_LENGTH],
            git_repository=git_repository,
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

    job_model, created = job_model_class.objects.get_or_create(
        source=job_source[:JOB_MAX_SOURCE_LENGTH],
        git_repository=git_repository,
        module_name=job_class.__module__[:JOB_MAX_NAME_LENGTH],
        job_class_name=job_class.__name__[:JOB_MAX_NAME_LENGTH],
        defaults={
            "slug": slugify(job_name)[:JOB_MAX_NAME_LENGTH],
            "grouping": job_class.grouping[:JOB_MAX_GROUPING_LENGTH],
            "name": job_name,
            "is_job_hook_receiver": issubclass(job_class, JobHookReceiver),
            "is_job_button_receiver": issubclass(job_class, JobButtonReceiver),
            "installed": True,
            "enabled": False,
        },
    )

    if job_name != default_job_name:
        job_model.name_override = True

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


def remove_prefix_from_cf_key(field_name):
    """
    field_name (str): f"cf_{cf.key}"

    Helper method to remove the "cf_" prefix
    """
    return field_name[3:]


def check_if_key_is_graphql_safe(model_name, key):
    """
    Helper method to check if a key field is Python/GraphQL safe.
    Used in CustomField for now, should be used in ComputedField and Relationship as well.
    """
    graphql_safe_pattern = re.compile("[_A-Za-z][_0-9A-Za-z]*")
    if not graphql_safe_pattern.fullmatch(key):
        raise ValidationError(
            {
                "key": "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace"
            }
        )


def migrate_role_data(
    model,
    role_model=None,
    is_choice_field=False,
    role_choiceset=None,
    legacy_role="legacy_role",
    new_role="new_role",
    is_m2m_field=False,
):
    """
    Migrate legacy_role's `role_model` equivalent record into new_role.

    Args:
        model(Model): Model with role field to alter
        role_model(Model): Role Model (optional)
        is_choice_field(bool): True if Model's role field is a choice field not an FK field else False
        role_choiceset(ChoiceSet): Role ChoiceSet (optional)
        legacy_role(str): Models role field legacy name; This is the current role field name
        new_role(str): Models role field new name; This is the name role field should be updated to
        is_m2m_field(bool): True if the role field is a ManyToManyField, else False
    """

    # Retrieve the queryset of `model` instances that have a value for the `legacy_role` field
    queryset = model.objects.filter(**{legacy_role + "__isnull": False}).only(*["pk", legacy_role])
    instances_to_update_data = get_instances_to_pk_and_new_role(
        queryset=queryset,
        role_model=role_model,
        role_choiceset=role_choiceset,
        legacy_role=legacy_role,
        new_role=new_role,
        is_m2m_field=is_m2m_field,
    )

    if instances_to_update_data:
        if is_m2m_field:
            # Update the new_role field using the set() method for ManyToManyFields
            for data in instances_to_update_data:
                instance = model.objects.get(pk=data["id"])
                getattr(instance, new_role).set(data[new_role])
        else:
            # Update the new_role field using the set() method for Foreign Key fields
            instances_to_update_data = [model(**data) for data in instances_to_update_data]
            model.objects.bulk_update(instances_to_update_data, fields=[new_role], batch_size=1000)


def get_instances_to_pk_and_new_role(queryset, role_model, role_choiceset, legacy_role, new_role, is_m2m_field):
    """
    Return a list of dictionaries containing the primary key and the new role value for each instance in the queryset.

    The new role value is determined by the following logic:
    - If `role_model` is not None, the value of the `legacy_role` field for each instance is used to
      query the `role_model` for a matching role. If a match is found, it is used as the new role value.
      If the `legacy_role` field is a ManyToManyField, all role names are obtained and used to query
      the `role_model`.
    - If `role_model` is None, the `legacy_role` field is assumed to be a ChoiceField, and the
      `role_choiceset` is used to look up the value corresponding to the label of the `legacy_role` field.
      This value is used as the new role value.

    Args:
        queryset (QuerySet): A queryset of instances to get the data for.
        role_model (Model): A model class to use to look up the new role value.
        role_choiceset (ChoiceSet): A `ChoiceSet` containing the choices for the new role field.
        legacy_role (str): The name of the field on each instance containing the legacy role value.
        new_role (str): The name of the field on each instance that will be updated with the new role value.
        is_m2m_field (bool): Whether the `legacy_role` field is a ManyToManyField.
    """
    data = []

    for item in queryset:
        role_equivalent = None
        if role_model:
            # Get the value for the legacy role field e.g. Device.role, IPAddress.role
            legacy_role_field = getattr(item, legacy_role)
            if is_m2m_field:
                # In the case of a m2m field, `legacy_role_field` we would need to get all role names e.g ConfigContext.roles.values_list("name", flat=True)
                role_names = legacy_role_field.values_list("name", flat=True)
                role_equivalent = role_model.objects.filter(Q(name__in=role_names) | Q(slug__in=role_names))
            else:
                if not isinstance(legacy_role_field, str):
                    legacy_role_field = legacy_role_field.name
                try:
                    role_equivalent = role_model.objects.get(Q(name=legacy_role_field) | Q(slug=legacy_role_field))
                except role_model.DoesNotExist:
                    logger.error(f"Role with name {legacy_role_field} not found")
        else:
            # ChoiceSet.CHOICES has to be inverted to obtain the value using its label
            # i.e {"vrf": "VRF"} --> {"VRF": "vrf"}
            inverted_role_choiceset = {label: value for value, label in role_choiceset.CHOICES}
            role_equivalent = inverted_role_choiceset.get(legacy_role_field)
        model_data = {"id": item.pk, new_role: role_equivalent}
        data.append(model_data)

    return data
