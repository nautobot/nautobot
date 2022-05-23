import django_filters
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.forms import DateField, IntegerField, NullBooleanField

from nautobot.dcim.models import DeviceRole, DeviceType, Platform, Region, Site
from nautobot.extras.utils import FeatureQuery, TaggableClassesQuery
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.filters import (
    BaseFilterSet,
    ContentTypeFilter,
    ContentTypeMultipleChoiceFilter,
    SearchFilter,
    TagFilter,
)
from nautobot.virtualization.models import Cluster, ClusterGroup
from .choices import (
    CustomFieldFilterLogicChoices,
    CustomFieldTypeChoices,
    JobResultStatusChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from .models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    DynamicGroup,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobLogEntry,
    JobResult,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    Tag,
    Webhook,
)


__all__ = (
    "ComputedFieldFilterSet",
    "ConfigContextFilterSet",
    "ContentTypeFilterSet",
    "CreatedUpdatedFilterSet",
    "CustomFieldFilter",
    "CustomFieldModelFilterSet",
    "CustomLinkFilterSet",
    "DynamicGroupFilterSet",
    "ExportTemplateFilterSet",
    "GitRepositoryFilterSet",
    "GraphQLQueryFilterSet",
    "ImageAttachmentFilterSet",
    "JobFilterSet",
    "JobLogEntryFilterSet",
    "JobResultFilterSet",
    "LocalContextFilterSet",
    "NautobotFilterSet",
    "ObjectChangeFilterSet",
    "RelationshipFilterSet",
    "RelationshipAssociationFilterSet",
    "ScheduledJobFilterSet",
    "SecretFilterSet",
    "SecretsGroupFilterSet",
    "SecretsGroupAssociationFilterSet",
    "StatusFilter",
    "StatusFilterSet",
    "StatusModelFilterSetMixin",
    "TagFilterSet",
    "WebhookFilterSet",
)


#
# Mixins
#


class CreatedUpdatedFilterSet(django_filters.FilterSet):
    created = django_filters.DateFilter()
    created__gte = django_filters.DateFilter(field_name="created", lookup_expr="gte")
    created__lte = django_filters.DateFilter(field_name="created", lookup_expr="lte")
    last_updated = django_filters.DateTimeFilter()
    last_updated__gte = django_filters.DateTimeFilter(field_name="last_updated", lookup_expr="gte")
    last_updated__lte = django_filters.DateTimeFilter(field_name="last_updated", lookup_expr="lte")


#
# Computed Fields
#


class ComputedFieldFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "target_url": "icontains",
            "text": "icontains",
            "content_type__app_label": "icontains",
            "content_type__model": "icontains",
        },
    )
    content_type = ContentTypeFilter()

    class Meta:
        model = ComputedField
        fields = (
            "content_type",
            "slug",
            "template",
            "fallback_value",
            "weight",
        )


#
# Config Contexts
#


class ConfigContextFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "data": "icontains",
        },
    )
    owner_content_type = ContentTypeFilter()
    region_id = django_filters.ModelMultipleChoiceFilter(
        field_name="regions",
        queryset=Region.objects.all(),
        label="Region",
    )
    region = django_filters.ModelMultipleChoiceFilter(
        field_name="regions__slug",
        queryset=Region.objects.all(),
        to_field_name="slug",
        label="Region (slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="sites",
        queryset=Site.objects.all(),
        label="Site",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="sites__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site (slug)",
    )
    role_id = django_filters.ModelMultipleChoiceFilter(
        field_name="roles",
        queryset=DeviceRole.objects.all(),
        label="Role",
    )
    role = django_filters.ModelMultipleChoiceFilter(
        field_name="roles__slug",
        queryset=DeviceRole.objects.all(),
        to_field_name="slug",
        label="Role (slug)",
    )
    device_type_id = django_filters.ModelMultipleChoiceFilter(
        field_name="device_types",
        queryset=DeviceType.objects.all(),
        label="Device Type",
    )
    device_type = django_filters.ModelMultipleChoiceFilter(
        field_name="device_types__slug",
        queryset=DeviceType.objects.all(),
        to_field_name="slug",
        label="Device Type (slug)",
    )
    platform_id = django_filters.ModelMultipleChoiceFilter(
        field_name="platforms",
        queryset=Platform.objects.all(),
        label="Platform",
    )
    platform = django_filters.ModelMultipleChoiceFilter(
        field_name="platforms__slug",
        queryset=Platform.objects.all(),
        to_field_name="slug",
        label="Platform (slug)",
    )
    cluster_group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster_groups",
        queryset=ClusterGroup.objects.all(),
        label="Cluster group",
    )
    cluster_group = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster_groups__slug",
        queryset=ClusterGroup.objects.all(),
        to_field_name="slug",
        label="Cluster group (slug)",
    )
    cluster_id = django_filters.ModelMultipleChoiceFilter(
        field_name="clusters",
        queryset=Cluster.objects.all(),
        label="Cluster",
    )
    tenant_group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="tenant_groups",
        queryset=TenantGroup.objects.all(),
        label="Tenant group",
    )
    tenant_group = django_filters.ModelMultipleChoiceFilter(
        field_name="tenant_groups__slug",
        queryset=TenantGroup.objects.all(),
        to_field_name="slug",
        label="Tenant group (slug)",
    )
    tenant_id = django_filters.ModelMultipleChoiceFilter(
        field_name="tenants",
        queryset=Tenant.objects.all(),
        label="Tenant",
    )
    tenant = django_filters.ModelMultipleChoiceFilter(
        field_name="tenants__slug",
        queryset=Tenant.objects.all(),
        to_field_name="slug",
        label="Tenant (slug)",
    )
    tag = django_filters.ModelMultipleChoiceFilter(
        field_name="tags__slug",
        queryset=Tag.objects.all(),
        to_field_name="slug",
        label="Tag (slug)",
    )

    class Meta:
        model = ConfigContext
        fields = ["id", "name", "is_active", "owner_content_type", "owner_object_id"]


#
# Filter for config context schema
#


class ConfigContextSchemaFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "data_schema": "icontains",
        },
    )
    owner_content_type = ContentTypeFilter()

    class Meta:
        model = ConfigContextSchema
        fields = [
            "id",
            "name",
            "description",
        ]


#
# ContentTypes
#


class ContentTypeFilterSet(django_filters.FilterSet):
    class Meta:
        model = ContentType
        fields = ["id", "app_label", "model"]


#
# Custom Fields
#


EXACT_FILTER_TYPES = (
    CustomFieldTypeChoices.TYPE_BOOLEAN,
    CustomFieldTypeChoices.TYPE_DATE,
    CustomFieldTypeChoices.TYPE_INTEGER,
    CustomFieldTypeChoices.TYPE_SELECT,
    CustomFieldTypeChoices.TYPE_MULTISELECT,
)


class CustomFieldFilter(django_filters.Filter):
    """
    Filter objects by the presence of a CustomFieldValue. The filter's name is used as the CustomField name.
    """

    def __init__(self, custom_field, *args, **kwargs):
        self.custom_field = custom_field

        if custom_field.type == CustomFieldTypeChoices.TYPE_INTEGER:
            self.field_class = IntegerField
        elif custom_field.type == CustomFieldTypeChoices.TYPE_BOOLEAN:
            self.field_class = NullBooleanField
        elif custom_field.type == CustomFieldTypeChoices.TYPE_DATE:
            self.field_class = DateField

        super().__init__(*args, **kwargs)

        self.field_name = f"_custom_field_data__{self.field_name}"

        if custom_field.type not in EXACT_FILTER_TYPES:
            if custom_field.filter_logic == CustomFieldFilterLogicChoices.FILTER_LOOSE:
                self.lookup_expr = "icontains"

        elif custom_field.type == CustomFieldTypeChoices.TYPE_MULTISELECT:
            # Contains handles lists within the JSON data for multi select fields
            self.lookup_expr = "contains"

    def filter(self, qs, value):
        if value == "null":
            return self.get_method(qs)(
                Q(**{f"{self.field_name}__exact": None}) | Q(**{f"{self.field_name}__isnull": True})
            )
        return super().filter(qs, value)


class CustomFieldModelFilterSet(django_filters.FilterSet):
    """
    Dynamically add a Filter for each CustomField applicable to the parent model.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        custom_fields = CustomField.objects.filter(
            content_types=ContentType.objects.get_for_model(self._meta.model)
        ).exclude(filter_logic=CustomFieldFilterLogicChoices.FILTER_DISABLED)
        for cf in custom_fields:
            self.filters["cf_{}".format(cf.name)] = CustomFieldFilter(field_name=cf.name, custom_field=cf)


class CustomFieldFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "label": "icontains",
            "description": "icontains",
        },
    )
    content_types = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("custom_fields").get_choices,
    )

    class Meta:
        model = CustomField
        fields = ["id", "content_types", "name", "required", "filter_logic", "weight"]


class CustomFieldChoiceFilterSet(BaseFilterSet):
    q = SearchFilter(filter_predicates={"value": "icontains"})
    field_id = django_filters.ModelMultipleChoiceFilter(
        field_name="field",
        queryset=CustomField.objects.all(),
        label="Field",
    )
    field = django_filters.ModelMultipleChoiceFilter(
        field_name="field__name",
        queryset=CustomField.objects.all(),
        to_field_name="name",
        label="Field (name)",
    )

    class Meta:
        model = CustomFieldChoice
        fields = ["id", "value", "weight"]


#
# Nautobot base filterset to use for most custom filterset classes.
#


class NautobotFilterSet(BaseFilterSet, CreatedUpdatedFilterSet, CustomFieldModelFilterSet):
    """
    This class exists to combine common functionality and is used as a base class throughout the
    codebase where all three of BaseFilterSet, CreatedUpdatedFilterSet and CustomFieldModelFilterSet
    are needed.
    """


#
# Custom Links
#


class CustomLinkFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "target_url": "icontains",
            "text": "icontains",
            "content_type__app_label": "icontains",
            "content_type__model": "icontains",
        },
    )
    content_type = ContentTypeFilter()

    class Meta:
        model = CustomLink
        fields = (
            "content_type",
            "name",
            "text",
            "target_url",
            "weight",
            "group_name",
            "button_class",
            "new_window",
        )


#
# Dynamic Groups
#


class DynamicGroupFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "slug": "icontains",
            "description": "icontains",
            "content_type__app_label": "icontains",
            "content_type__model": "icontains",
        },
    )
    content_type = ContentTypeMultipleChoiceFilter(choices=FeatureQuery("dynamic_groups").get_choices, conjoined=False)

    class Meta:
        model = DynamicGroup
        fields = ("id", "name", "slug", "description")


#
# Export Templates
#


class ExportTemplateFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "owner_content_type__app_label": "icontains",
            "owner_content_type__model": "icontains",
            "content_type__app_label": "icontains",
            "content_type__model": "icontains",
            "description": "icontains",
        },
    )
    owner_content_type = ContentTypeFilter()

    class Meta:
        model = ExportTemplate
        fields = ["id", "content_type", "owner_content_type", "owner_object_id", "name"]


#
# Datasources (Git)
#


class GitRepositoryFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "remote_url": "icontains",
            "branch": "icontains",
        },
    )
    secrets_group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="secrets_group",
        queryset=SecretsGroup.objects.all(),
        label="Secrets group (ID)",
    )
    secrets_group = django_filters.ModelMultipleChoiceFilter(
        field_name="secrets_group__slug",
        queryset=SecretsGroup.objects.all(),
        to_field_name="slug",
        label="Secrets group (slug)",
    )
    tag = TagFilter()

    class Meta:
        model = GitRepository
        fields = ["id", "name", "slug", "remote_url", "branch"]


#
# GraphQL Queries
#


class GraphQLQueryFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "slug": "icontains",
            "query": "icontains",
        },
    )

    class Meta:
        model = GraphQLQuery
        fields = ["name", "slug"]


#
# Image Attachments
#


class ImageAttachmentFilterSet(BaseFilterSet):
    content_type = ContentTypeFilter()

    class Meta:
        model = ImageAttachment
        fields = ["id", "content_type_id", "object_id", "name"]


#
# Jobs
#


class JobFilterSet(BaseFilterSet, CustomFieldModelFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "slug": "icontains",
            "grouping": "icontains",
            "description": "icontains",
        },
    )
    tag = TagFilter()

    class Meta:
        model = Job
        fields = [
            "id",
            "source",
            "module_name",
            "job_class_name",
            "slug",
            "name",
            "grouping",
            "installed",
            "enabled",
            "approval_required",
            "commit_default",
            "hidden",
            "read_only",
            "soft_time_limit",
            "time_limit",
            "grouping_override",
            "name_override",
            "approval_required_override",
            "description_override",
            "commit_default_override",
            "hidden_override",
            "read_only_override",
            "soft_time_limit_override",
            "time_limit_override",
        ]


class JobResultFilterSet(BaseFilterSet, CustomFieldModelFilterSet):
    q = SearchFilter(
        filter_predicates={
            "job_model__name": "icontains",
            "name": "icontains",
            "user__username": "icontains",
        },
    )
    job_model = django_filters.ModelMultipleChoiceFilter(
        field_name="job_model__slug",
        queryset=Job.objects.all(),
        to_field_name="slug",
        label="Job (slug)",
    )
    job_model_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Job.objects.all(),
        label="Job (ID)",
    )
    obj_type = ContentTypeFilter()
    created = django_filters.DateTimeFilter()
    completed = django_filters.DateTimeFilter()
    status = django_filters.MultipleChoiceFilter(choices=JobResultStatusChoices, null_value=None)

    class Meta:
        model = JobResult
        fields = ["id", "created", "completed", "status", "user", "obj_type", "name"]


class JobLogEntryFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "grouping": "icontains",
            "message": "icontains",
            "log_level": "icontains",
        },
    )

    class Meta:
        model = JobLogEntry
        exclude = []


class ScheduledJobFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "job_class": "icontains",
            "description": "icontains",
        },
    )
    job_model = django_filters.ModelMultipleChoiceFilter(
        field_name="job_model__slug",
        queryset=Job.objects.all(),
        to_field_name="slug",
        label="Job (slug)",
    )
    job_model_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Job.objects.all(),
        label="Job (ID)",
    )

    first_run = django_filters.DateTimeFilter()
    last_run = django_filters.DateTimeFilter()

    class Meta:
        model = ScheduledJob
        fields = ["id", "name", "total_run_count"]


#
# Filter for Local Config Context Data
#


class LocalContextFilterSet(django_filters.FilterSet):
    local_context_data = django_filters.BooleanFilter(
        method="_local_context_data",
        label="Has local config context data",
    )
    local_context_schema_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ConfigContextSchema.objects.all(),
        label="Schema (ID)",
    )
    local_context_schema = django_filters.ModelMultipleChoiceFilter(
        field_name="local_context_schema__slug",
        queryset=ConfigContextSchema.objects.all(),
        to_field_name="slug",
        label="Schema (slug)",
    )

    def _local_context_data(self, queryset, name, value):
        return queryset.exclude(local_context_data__isnull=value)


class ObjectChangeFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "user_name": "icontains",
            "object_repr": "icontains",
        },
    )
    changed_object_type = ContentTypeFilter()
    user_id = django_filters.ModelMultipleChoiceFilter(
        queryset=get_user_model().objects.all(),
        label="User (ID)",
    )
    user = django_filters.ModelMultipleChoiceFilter(
        field_name="user__username",
        queryset=get_user_model().objects.all(),
        to_field_name="username",
        label="User name",
    )

    class Meta:
        model = ObjectChange
        fields = [
            "id",
            "user",
            "user_name",
            "request_id",
            "action",
            "changed_object_type_id",
            "changed_object_id",
            "object_repr",
            "time",
        ]


#
# Relationships
#


class RelationshipFilterSet(BaseFilterSet):

    source_type = ContentTypeMultipleChoiceFilter(choices=FeatureQuery("relationships").get_choices, conjoined=False)
    destination_type = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("relationships").get_choices, conjoined=False
    )

    class Meta:
        model = Relationship
        fields = ["id", "name", "type", "source_type", "destination_type"]


class RelationshipAssociationFilterSet(BaseFilterSet):

    relationship = django_filters.ModelMultipleChoiceFilter(
        field_name="relationship__slug",
        queryset=Relationship.objects.all(),
        to_field_name="slug",
        label="Relationship (slug)",
    )
    source_type = ContentTypeMultipleChoiceFilter(choices=FeatureQuery("relationships").get_choices, conjoined=False)
    destination_type = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("relationships").get_choices, conjoined=False
    )

    class Meta:
        model = RelationshipAssociation
        fields = ["id", "relationship", "source_type", "source_id", "destination_type", "destination_id"]


#
# Secrets
#


class SecretFilterSet(
    BaseFilterSet,
    CustomFieldModelFilterSet,
    CreatedUpdatedFilterSet,
):
    """Filterset for the Secret model."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "slug": "icontains",
        },
    )
    # TODO dynamic choices needed
    # provider = django_filters.MultipleChoiceFilter(choices=..., null_value=None)

    class Meta:
        model = Secret
        fields = ("id", "name", "slug", "provider", "created", "last_updated")


class SecretsGroupFilterSet(
    BaseFilterSet,
    CustomFieldModelFilterSet,
    CreatedUpdatedFilterSet,
):
    """Filterset for the SecretsGroup model."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "slug": "icontains",
        },
    )

    class Meta:
        model = SecretsGroup
        fields = ("id", "name", "slug", "created", "last_updated")


class SecretsGroupAssociationFilterSet(BaseFilterSet):
    """Filterset for the SecretsGroupAssociation through model."""

    group_id = django_filters.ModelMultipleChoiceFilter(
        queryset=SecretsGroup.objects.all(),
        label="Group (ID)",
    )
    group = django_filters.ModelMultipleChoiceFilter(
        queryset=SecretsGroup.objects.all(),
        field_name="group__slug",
        to_field_name="slug",
        label="Group (slug)",
    )
    secret_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Secret.objects.all(),
        label="Secret (ID)",
    )
    secret = django_filters.ModelMultipleChoiceFilter(
        queryset=Secret.objects.all(),
        field_name="secret__slug",
        to_field_name="slug",
        label="Secret (slug)",
    )
    access_type = django_filters.MultipleChoiceFilter(choices=SecretsGroupAccessTypeChoices)
    secret_type = django_filters.MultipleChoiceFilter(choices=SecretsGroupSecretTypeChoices)

    class Meta:
        model = SecretsGroupAssociation
        fields = ("id",)


#
# Statuses
#


class StatusFilter(django_filters.ModelMultipleChoiceFilter):
    """
    Filter field used for filtering Status fields.

    Explicitly sets `to_field_name='value'` and dynamically sets queryset to
    retrieve choices for the corresponding model & field name bound to the
    filterset.
    """

    def __init__(self, *args, **kwargs):
        kwargs["to_field_name"] = "slug"
        super().__init__(*args, **kwargs)

    def get_queryset(self, request):
        self.queryset = Status.objects.all()
        return super().get_queryset(request)

    def get_filter_predicate(self, value):
        """Always use the field's name and the `to_field_name` attribute as predicate."""
        # e.g. `status__slug`
        to_field_name = self.field.to_field_name
        name = f"{self.field_name}__{to_field_name}"
        return {name: getattr(value, to_field_name)}


class StatusFilterSet(NautobotFilterSet):
    """API filter for filtering custom status object fields."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "slug": "icontains",
            "content_types__model": "icontains",
        },
    )
    content_types = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("statuses").get_choices,
    )

    class Meta:
        model = Status
        fields = [
            "id",
            "content_types",
            "color",
            "name",
            "slug",
            "created",
            "last_updated",
        ]


class StatusModelFilterSetMixin(django_filters.FilterSet):
    """
    Mixin to add a `status` filter field to a FilterSet.
    """

    status = StatusFilter()


#
# Tags
#


class TagFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "slug": "icontains",
            "content_types__model": "icontains",
        },
    )
    content_types = ContentTypeMultipleChoiceFilter(
        choices=TaggableClassesQuery().get_choices,
    )

    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "color", "content_types"]


#
# Webhooks
#


class WebhookFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "payload_url": "icontains",
            "additional_headers": "icontains",
            "body_template": "icontains",
        },
    )
    content_types = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("webhooks").get_choices,
    )

    class Meta:
        model = Webhook
        fields = [
            "name",
            "payload_url",
            "enabled",
            "content_types",
            "type_create",
            "type_update",
            "type_delete",
        ]
