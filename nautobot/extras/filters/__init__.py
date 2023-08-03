import django_filters
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import DeviceRedundancyGroup, DeviceRole, DeviceType, Location, Platform, Region, Site
from nautobot.extras.choices import (
    JobResultStatusChoices,
    RelationshipTypeChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.extras.filters.customfields import (
    CustomFieldBooleanFilter,
    CustomFieldCharFilter,
    CustomFieldDateFilter,
    CustomFieldFilterMixin,
    CustomFieldJSONFilter,
    CustomFieldMultiSelectFilter,
    CustomFieldMultiValueCharFilter,
    CustomFieldMultiValueDateFilter,
    CustomFieldMultiValueNumberFilter,
    CustomFieldNumberFilter,
)
from nautobot.extras.filters.mixins import (
    CustomFieldModelFilterSetMixin,
    CreatedUpdatedModelFilterSetMixin,
    LocalContextModelFilterSetMixin,
    RelationshipFilter,
    RelationshipModelFilterSetMixin,
    StatusFilter,
    StatusModelFilterSetMixin,
)
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    DynamicGroup,
    DynamicGroupMembership,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobButton,
    JobHook,
    JobLogEntry,
    JobResult,
    Note,
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
from nautobot.extras.utils import ChangeLoggedModelsQuery, FeatureQuery, TaggableClassesQuery
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.deprecation import class_deprecated_in_favor_of
from nautobot.utilities.filters import (
    BaseFilterSet,
    ContentTypeFilter,
    ContentTypeMultipleChoiceFilter,
    MultiValueUUIDFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
    SearchFilter,
    TagFilter,
)
from nautobot.virtualization.models import Cluster, ClusterGroup


__all__ = (
    "ComputedFieldFilterSet",
    "ConfigContextFilterSet",
    "ContentTypeFilterSet",
    "ContentTypeMultipleChoiceFilter",
    "CreatedUpdatedFilterSet",
    "CreatedUpdatedModelFilterSetMixin",
    "CustomFieldBooleanFilter",
    "CustomFieldCharFilter",
    "CustomFieldDateFilter",
    "CustomFieldFilterMixin",
    "CustomFieldJSONFilter",
    "CustomFieldMultiSelectFilter",
    "CustomFieldMultiValueCharFilter",
    "CustomFieldMultiValueDateFilter",
    "CustomFieldMultiValueNumberFilter",
    "CustomFieldNumberFilter",
    "CustomFieldModelFilterSet",
    "CustomFieldModelFilterSetMixin",
    "CustomLinkFilterSet",
    "DynamicGroupFilterSet",
    "DynamicGroupMembershipFilterSet",
    "ExportTemplateFilterSet",
    "GitRepositoryFilterSet",
    "GraphQLQueryFilterSet",
    "ImageAttachmentFilterSet",
    "JobFilterSet",
    "JobLogEntryFilterSet",
    "JobResultFilterSet",
    "LocalContextFilterSet",
    "LocalContextModelFilterSetMixin",
    "NautobotFilterSet",
    "NoteFilterSet",
    "ObjectChangeFilterSet",
    "RelationshipFilter",
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


# TODO: remove in 2.2
@class_deprecated_in_favor_of(CreatedUpdatedModelFilterSetMixin)
class CreatedUpdatedFilterSet(CreatedUpdatedModelFilterSetMixin):
    pass


@class_deprecated_in_favor_of(RelationshipModelFilterSetMixin)
class RelationshipModelFilterSet(RelationshipModelFilterSetMixin):
    pass


#
# Computed Fields
#


class ComputedFieldFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "label": "icontains",
            "description": "icontains",
            "content_type__app_label": "icontains",
            "content_type__model": "icontains",
            "template": "icontains",
            "fallback_value": "icontains",
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
    schema = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="schema",
        queryset=ConfigContextSchema.objects.all(),
        to_field_name="slug",
        label="Schema (slug or PK)",
    )
    region_id = django_filters.ModelMultipleChoiceFilter(
        field_name="regions",
        queryset=Region.objects.all(),
        label="Region (ID) - Deprecated (use region filter)",
    )
    region = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="regions",
        queryset=Region.objects.all(),
        label="Region (ID or slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="sites",
        queryset=Site.objects.all(),
        label="Site (ID) - Deprecated (use site filter)",
    )
    site = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="sites",
        queryset=Site.objects.all(),
        label="Site (ID or slug)",
    )
    location_id = django_filters.ModelMultipleChoiceFilter(
        field_name="locations",
        queryset=Location.objects.all(),
        label="Location (ID) - Deprecated (use location filter)",
    )
    location = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="locations",
        queryset=Location.objects.all(),
        label="Location (ID or slug)",
    )
    role_id = django_filters.ModelMultipleChoiceFilter(
        field_name="roles",
        queryset=DeviceRole.objects.all(),
        label="Role (ID) - Deprecated (use role filter)",
    )
    role = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="roles",
        queryset=DeviceRole.objects.all(),
        label="Role (ID or slug)",
    )
    device_type_id = django_filters.ModelMultipleChoiceFilter(
        field_name="device_types",
        queryset=DeviceType.objects.all(),
        label="Device Type (ID) - Deprecated (use device_type filter)",
    )
    device_type = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device_types",
        queryset=DeviceType.objects.all(),
        label="Device Type (ID or slug)",
    )
    platform_id = django_filters.ModelMultipleChoiceFilter(
        field_name="platforms",
        queryset=Platform.objects.all(),
        label="Platform (ID) - Deprecated (use platform filter)",
    )
    platform = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="platforms",
        queryset=Platform.objects.all(),
        label="Platform (ID or slug)",
    )
    cluster_group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster_groups",
        queryset=ClusterGroup.objects.all(),
        label="Cluster group (ID) - Deprecated (use cluster_group filter)",
    )
    cluster_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="cluster_groups",
        queryset=ClusterGroup.objects.all(),
        label="Cluster group (ID or slug)",
    )
    cluster_id = django_filters.ModelMultipleChoiceFilter(
        field_name="clusters",
        queryset=Cluster.objects.all(),
        label="Cluster (ID)",
    )
    tenant_group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="tenant_groups",
        queryset=TenantGroup.objects.all(),
        label="Tenant group (ID) - Deprecated (use tenant_group filter)",
    )
    tenant_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="tenant_groups",
        queryset=TenantGroup.objects.all(),
        label="Tenant group (ID or slug)",
    )
    tenant_id = django_filters.ModelMultipleChoiceFilter(
        field_name="tenants",
        queryset=Tenant.objects.all(),
        label="Tenant (ID) - Deprecated (use tenant filter)",
    )
    tenant = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="tenants",
        queryset=Tenant.objects.all(),
        label="Tenant (ID or slug)",
    )
    device_redundancy_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device_redundancy_groups",
        queryset=DeviceRedundancyGroup.objects.all(),
        to_field_name="slug",
        label="Device Redundancy Group (slug or PK)",
    )
    tag = django_filters.ModelMultipleChoiceFilter(
        field_name="tags__slug",
        queryset=Tag.objects.all(),
        to_field_name="slug",
        label="Tag (slug)",
    )

    # Conditional enablement of dynamic groups filtering
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if settings.CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED:
            self.filters["dynamic_groups"] = NaturalKeyOrPKMultipleChoiceFilter(
                queryset=DynamicGroup.objects.all(),
                label="Dynamic Groups (slug or ID)",
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


class ContentTypeFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "app_label": "icontains",
            "model": "icontains",
        },
    )

    class Meta:
        model = ContentType
        fields = ["id", "app_label", "model"]


# TODO: remove in 2.2
@class_deprecated_in_favor_of(CustomFieldModelFilterSetMixin)
class CustomFieldModelFilterSet(CustomFieldModelFilterSetMixin):
    pass


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
        label="Field (ID) - Deprecated (use field filter)",
    )
    field = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=CustomField.objects.all(),
        to_field_name="name",
        label="Field (ID or name)",
    )

    class Meta:
        model = CustomFieldChoice
        fields = ["id", "value", "weight"]


#
# Nautobot base filterset to use for most custom filterset classes.
#


class NautobotFilterSet(
    BaseFilterSet,
    CreatedUpdatedModelFilterSetMixin,
    RelationshipModelFilterSetMixin,
    CustomFieldModelFilterSetMixin,
):
    """
    This class exists to combine common functionality and is used as a base class throughout the codebase where all of
    BaseFilterSet, CreatedUpdatedModelFilterSetMixin, RelationshipModelFilterSetMixin and CustomFieldModelFilterSetMixin
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


class DynamicGroupMembershipFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "operator": "icontains",
            "group__name": "icontains",
            "group__slug": "icontains",
            "parent_group__name": "icontains",
            "parent_group__slug": "icontains",
        },
    )
    group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DynamicGroup.objects.all(),
        label="Group (slug or ID)",
    )
    parent_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DynamicGroup.objects.all(),
        label="Parent Group (slug or ID)",
    )

    class Meta:
        model = DynamicGroupMembership
        fields = ("id", "group", "parent_group", "operator", "weight")


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
        label="Secrets group (ID) - Deprecated (use secrets_group filter)",
    )
    secrets_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SecretsGroup.objects.all(),
        label="Secrets group (ID or slug)",
    )
    tag = TagFilter()

    class Meta:
        model = GitRepository
        fields = ["id", "name", "slug", "remote_url", "branch", "provided_contents"]


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


class JobFilterSet(BaseFilterSet, CustomFieldModelFilterSetMixin):
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
            "has_sensitive_variables",
            "approval_required",
            "commit_default",
            "hidden",
            "read_only",
            "is_job_hook_receiver",
            "is_job_button_receiver",
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
            "has_sensitive_variables_override",
        ]


class JobHookFilterSet(BaseFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains", "slug": "icontains"})
    content_types = ContentTypeMultipleChoiceFilter(
        choices=ChangeLoggedModelsQuery().get_choices,
    )
    job = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Job.objects.all(),
        label="Job (slug or ID)",
    )

    class Meta:
        model = JobHook
        fields = [
            "name",
            "content_types",
            "enabled",
            "job",
            "slug",
            "type_create",
            "type_update",
            "type_delete",
        ]


class JobResultFilterSet(BaseFilterSet, CustomFieldModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "job_model__name": "icontains",
            "name": "icontains",
            "user__username": "icontains",
        },
    )
    job_model = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Job.objects.all(),
        label="Job (ID or slug)",
    )
    job_model_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Job.objects.all(),
        label="Job (ID) - Deprecated (use job_model filter)",
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
    job_model = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="job_model__slug",
        queryset=Job.objects.all(),
        label="Job (ID or slug)",
    )
    job_model_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Job.objects.all(),
        label="Job (ID) - Deprecated (use job_model filter)",
    )

    first_run = django_filters.DateTimeFilter()
    last_run = django_filters.DateTimeFilter()

    class Meta:
        model = ScheduledJob
        fields = ["id", "name", "total_run_count"]


#
# Job Button
#


class JobButtonFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "job__name": "icontains",
            "text": "icontains",
        },
    )
    content_types = ContentTypeFilter()
    job = NaturalKeyOrPKMultipleChoiceFilter(queryset=Job.objects.all(), label="Job (slug or ID)")

    class Meta:
        model = JobButton
        fields = (
            "content_types",
            "name",
            "text",
            "job",
            "weight",
            "group_name",
            "button_class",
            "confirmation",
        )


#
# Filter for Local Config Context Data
#


# TODO: remove in 2.2
@class_deprecated_in_favor_of(LocalContextModelFilterSetMixin)
class LocalContextFilterSet(LocalContextModelFilterSetMixin):
    pass


class NoteFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "user_name": "icontains",
            "note": "icontains",
            "assigned_object_id": "exact",
        },
    )
    assigned_object_type = ContentTypeFilter()
    user = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="username",
        queryset=get_user_model().objects.all(),
        label="User (username or ID)",
    )

    class Meta:
        model = Note
        fields = [
            "id",
            "user",
            "user_name",
            "assigned_object_type_id",
            "assigned_object_id",
            "note",
        ]


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
        label="User (ID) - Deprecated (use user filter)",
    )
    user = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=get_user_model().objects.all(),
        to_field_name="username",
        label="User name (ID or username)",
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
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        }
    )

    source_type = ContentTypeMultipleChoiceFilter(choices=FeatureQuery("relationships").get_choices, conjoined=False)
    destination_type = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("relationships").get_choices, conjoined=False
    )

    class Meta:
        model = Relationship
        fields = ["id", "name", "slug", "type", "source_type", "destination_type"]


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
    peer_id = MultiValueUUIDFilter(method="peer_id_filter")

    class Meta:
        model = RelationshipAssociation
        fields = ["id", "relationship", "source_type", "source_id", "destination_type", "destination_id", "peer_id"]

    def peer_id_filter(self, queryset, name, value):
        # Filter down to symmetric relationships only.
        queryset = queryset.filter(
            relationship__type__in=[
                RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
                RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
            ]
        )
        # Then Filter based on peer_id.
        queryset = queryset.filter(source_id__in=value) | queryset.filter(destination_id__in=value)
        return queryset


#
# Secrets
#


class SecretFilterSet(
    BaseFilterSet,
    CustomFieldModelFilterSetMixin,
    CreatedUpdatedModelFilterSetMixin,
):
    """Filterset for the Secret model."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "slug": "icontains",
        },
    )
    # TODO(Glenn): dynamic choices needed. The issue being that secrets providers are Python
    # classes, not database models.
    # provider = django_filters.MultipleChoiceFilter(choices=..., null_value=None)

    class Meta:
        model = Secret
        fields = ("id", "name", "slug", "provider", "created", "last_updated")


class SecretsGroupFilterSet(
    BaseFilterSet,
    CustomFieldModelFilterSetMixin,
    CreatedUpdatedModelFilterSetMixin,
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
        label="Group (ID) - Deprecated (use group filter)",
    )
    group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SecretsGroup.objects.all(),
        label="Group (ID or slug)",
    )
    secret_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Secret.objects.all(),
        label="Secret (ID) - Deprecated (use secret filter)",
    )
    secret = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Secret.objects.all(),
        label="Secret (ID or slug)",
    )
    access_type = django_filters.MultipleChoiceFilter(choices=SecretsGroupAccessTypeChoices)
    secret_type = django_filters.MultipleChoiceFilter(choices=SecretsGroupSecretTypeChoices)

    class Meta:
        model = SecretsGroupAssociation
        fields = ("id",)


#
# Statuses
#


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
