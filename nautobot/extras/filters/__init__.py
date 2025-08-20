from difflib import get_close_matches
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
import django_filters
from drf_spectacular.utils import extend_schema_field
from timezone_field import TimeZoneField

from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.filters import (
    BaseFilterSet,
    ContentTypeFilter,
    ContentTypeMultipleChoiceFilter,
    MultiValueUUIDFilter,
    NameSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
)
from nautobot.core.utils.deprecation import class_deprecated_in_favor_of
from nautobot.dcim.models import DeviceRedundancyGroup, DeviceType, Location, Platform
from nautobot.extras.choices import (
    JobQueueTypeChoices,
    JobResultStatusChoices,
    MetadataTypeDataTypeChoices,
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
    ConfigContextRoleFilter,
    CreatedUpdatedModelFilterSetMixin,
    CustomFieldModelFilterSetMixin,
    LocalContextModelFilterSetMixin,
    RelationshipFilter,
    RelationshipModelFilterSetMixin,
    RoleModelFilterSetMixin,
    StatusFilter,
    StatusModelFilterSetMixin,
)
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    Contact,
    ContactAssociation,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    DynamicGroup,
    DynamicGroupMembership,
    ExportTemplate,
    ExternalIntegration,
    FileProxy,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobButton,
    JobHook,
    JobLogEntry,
    JobQueue,
    JobQueueAssignment,
    JobResult,
    MetadataChoice,
    MetadataType,
    Note,
    ObjectChange,
    ObjectMetadata,
    Relationship,
    RelationshipAssociation,
    Role,
    SavedView,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    StaticGroupAssociation,
    Status,
    Tag,
    Team,
    UserSavedViewAssociation,
    Webhook,
)
from nautobot.extras.utils import (
    ChangeLoggedModelsQuery,
    FeatureQuery,
    RoleModelsQuery,
    TaggableClassesQuery,
)
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.virtualization.models import Cluster, ClusterGroup

__all__ = (
    "ComputedFieldFilterSet",
    "ConfigContextFilterSet",
    "ContactFilterSet",
    "ContentTypeFilterSet",
    "ContentTypeMultipleChoiceFilter",
    "CreatedUpdatedFilterSet",
    "CreatedUpdatedModelFilterSetMixin",
    "CustomFieldBooleanFilter",
    "CustomFieldCharFilter",
    "CustomFieldDateFilter",
    "CustomFieldFilterMixin",
    "CustomFieldJSONFilter",
    "CustomFieldModelFilterSet",
    "CustomFieldModelFilterSetMixin",
    "CustomFieldMultiSelectFilter",
    "CustomFieldMultiValueCharFilter",
    "CustomFieldMultiValueDateFilter",
    "CustomFieldMultiValueNumberFilter",
    "CustomFieldNumberFilter",
    "CustomLinkFilterSet",
    "DynamicGroupFilterSet",
    "DynamicGroupMembershipFilterSet",
    "ExportTemplateFilterSet",
    "FileProxyFilterSet",
    "GitRepositoryFilterSet",
    "GraphQLQueryFilterSet",
    "ImageAttachmentFilterSet",
    "JobFilterSet",
    "JobLogEntryFilterSet",
    "JobQueueAssignmentFilterSet",
    "JobQueueFilterSet",
    "JobResultFilterSet",
    "LocalContextFilterSet",
    "LocalContextModelFilterSetMixin",
    "MetadataChoiceFilterSet",
    "MetadataTypeFilterSet",
    "NautobotFilterSet",
    "NoteFilterSet",
    "ObjectChangeFilterSet",
    "RelationshipAssociationFilterSet",
    "RelationshipFilter",
    "RelationshipFilterSet",
    "RoleFilterSet",
    "RoleModelFilterSetMixin",
    "ScheduledJobFilterSet",
    "SecretFilterSet",
    "SecretsGroupAssociationFilterSet",
    "SecretsGroupFilterSet",
    "StatusFilter",
    "StatusFilterSet",
    "StatusModelFilterSetMixin",
    "TagFilterSet",
    "TeamFilterSet",
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
            "grouping": "icontains",
            "template": "icontains",
            "fallback_value": "icontains",
        },
    )
    content_type = ContentTypeFilter()

    class Meta:
        model = ComputedField
        fields = (
            "content_type",
            "key",
            "grouping",
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
        field_name="config_context_schema",
        queryset=ConfigContextSchema.objects.all(),
        to_field_name="name",
        label="Schema (name or PK)",
    )
    location_id = django_filters.ModelMultipleChoiceFilter(
        field_name="locations",
        queryset=Location.objects.all(),
        label="Location (ID) - Deprecated (use location filter)",
    )
    location = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="locations",
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Location (name or ID)",
    )
    device_type_id = django_filters.ModelMultipleChoiceFilter(
        field_name="device_types",
        queryset=DeviceType.objects.all(),
        label="Device Type (ID) - Deprecated (use device_type filter)",
    )
    device_type = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device_types",
        queryset=DeviceType.objects.all(),
        to_field_name="model",
        label="Device Type (model or ID)",
    )
    platform_id = django_filters.ModelMultipleChoiceFilter(
        field_name="platforms",
        queryset=Platform.objects.all(),
        label="Platform (ID) - Deprecated (use platform filter)",
    )
    platform = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="platforms",
        queryset=Platform.objects.all(),
        to_field_name="name",
        label="Platform (ID or name)",
    )
    cluster_group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster_groups",
        queryset=ClusterGroup.objects.all(),
        label="Cluster group (ID) - Deprecated (use cluster_group filter)",
    )
    cluster_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="cluster_groups",
        queryset=ClusterGroup.objects.all(),
        to_field_name="name",
        label="Cluster group (ID or name)",
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
        label="Tenant group (ID or name)",
        to_field_name="name",
    )
    tenant_id = django_filters.ModelMultipleChoiceFilter(
        field_name="tenants",
        queryset=Tenant.objects.all(),
        label="Tenant (ID) - Deprecated (use tenant filter)",
    )
    tenant = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="tenants",
        queryset=Tenant.objects.all(),
        label="Tenant (ID or name)",
        to_field_name="name",
    )
    device_redundancy_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device_redundancy_groups",
        queryset=DeviceRedundancyGroup.objects.all(),
        to_field_name="name",
        label="Device Redundancy Group (name or PK)",
    )
    tag = django_filters.ModelMultipleChoiceFilter(
        field_name="tags",
        queryset=Tag.objects.all(),
        to_field_name="name",
        label="Tag (name)",
    )
    role = ConfigContextRoleFilter()

    # Conditional enablement of dynamic groups filtering
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if settings.CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED:
            self.filters["dynamic_groups"] = NaturalKeyOrPKMultipleChoiceFilter(
                queryset=DynamicGroup.objects.all(),
                label="Dynamic Groups (name or ID)",
                to_field_name="name",
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
    can_add = django_filters.BooleanFilter(method="_can_add", label="User can add objects of this type")
    can_change = django_filters.BooleanFilter(method="_can_change", label="User can change objects of this type")
    can_delete = django_filters.BooleanFilter(method="_can_delete", label="User can delete objects of this type")
    can_view = django_filters.BooleanFilter(method="_can_view", label="User can view objects of this type")
    has_serializer = django_filters.BooleanFilter(
        method="_has_serializer", label="A REST API serializer exists for this type"
    )
    feature = django_filters.CharFilter(method="_feature", label="Objects of this type support the named feature")

    class Meta:
        model = ContentType
        fields = ["id", "app_label", "model"]

    def _can_action(self, queryset, name, value, action):
        if not self.request or not self.request.user:
            if value:
                return queryset.none()
            else:
                return queryset
        ct_pks = [
            ct.pk for ct in queryset if value == self.request.user.has_perm(f"{ct.app_label}.{action}_{ct.model}")
        ]
        return queryset.filter(pk__in=ct_pks)

    def _can_add(self, queryset, name, value):
        return self._can_action(queryset, name, value, action="add")

    def _can_change(self, queryset, name, value):
        return self._can_action(queryset, name, value, action="change")

    def _can_delete(self, queryset, name, value):
        return self._can_action(queryset, name, value, action="delete")

    def _can_view(self, queryset, name, value):
        return self._can_action(queryset, name, value, action="view")

    def _has_serializer(self, queryset, name, value):
        ct_pks = []
        for ct in queryset:
            model = ct.model_class()
            if not model:
                continue
            try:
                get_serializer_for_model(model)
            except SerializerNotFound:
                continue
            ct_pks.append(ct.pk)
        if value:
            return queryset.filter(pk__in=ct_pks)
        else:
            return queryset.exclude(pk__in=ct_pks)

    def _feature(self, queryset, name, value):
        return queryset.filter(FeatureQuery(value).get_query())


# TODO: remove in 2.2
@class_deprecated_in_favor_of(CustomFieldModelFilterSetMixin)
class CustomFieldModelFilterSet(CustomFieldModelFilterSetMixin):
    pass


class CustomFieldFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "label": "icontains",
            "description": "icontains",
            "grouping": "icontains",
        },
    )
    content_types = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("custom_fields").get_choices,
    )

    class Meta:
        model = CustomField
        fields = ["id", "content_types", "label", "grouping", "required", "filter_logic", "weight"]


class CustomFieldChoiceFilterSet(BaseFilterSet):
    q = SearchFilter(filter_predicates={"value": "icontains"})
    custom_field = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=CustomField.objects.all(),
        to_field_name="key",
        label="Field (ID or Key)",
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
# Contacts
#


class ContactTeamFilterSet(NameSearchFilterSet, NautobotFilterSet):
    """Base filter set for Contacts and Teams."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "email": "icontains",
            "phone": "icontains",
        },
    )

    similar_to_location_data = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Location.objects.all(),
        label="Similar to location contact data",
        method="_similar_to_location_data",
    )

    def generate_query__similar_to_location_data(self, queryset, locations):
        """Helper method used by _similar_to_location_data() method."""
        query_params = Q()
        for location in locations:
            contact_name = location.contact_name
            contact_phone = location.contact_phone
            contact_email = location.contact_email
            if contact_name:
                contact_names = list(queryset.order_by().values_list("name", flat=True).distinct())
                name_matches = get_close_matches(contact_name, contact_names, cutoff=0.8)
                if name_matches:
                    query_params |= Q(name__in=name_matches)
            if contact_phone:
                contact_phones = list(queryset.order_by().values_list("phone", flat=True).distinct())
                phone_matches = get_close_matches(contact_phone, contact_phones, cutoff=0.8)
                if phone_matches:
                    query_params |= Q(phone__in=phone_matches)
            if contact_email:
                contact_emails = list(queryset.order_by().values_list("email", flat=True).distinct())
                # fuzzy matching for emails doesn't make sense, use case insensitive match here
                email_matches = [e for e in contact_emails if e.casefold() == contact_email.casefold()]
                if email_matches:
                    query_params |= Q(email__in=email_matches)

        return query_params

    @extend_schema_field({"type": "string"})
    def _similar_to_location_data(self, queryset, name, value):
        """FilterSet method for getting Contacts or Teams that are similar to the explicit contact fields of a location"""
        if value:
            params = self.generate_query__similar_to_location_data(queryset, value)
            if len(params) > 0:
                return queryset.filter(params)
            else:
                return queryset.none()
        return queryset


class ContactFilterSet(ContactTeamFilterSet):
    teams = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Team.objects.all(),
        to_field_name="name",
        label="Team (name or ID)",
    )

    class Meta:
        model = Contact
        fields = "__all__"


class ContactAssociationFilterSet(NautobotFilterSet, StatusModelFilterSetMixin, RoleModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "contact__name": "icontains",
            "team__name": "icontains",
        },
    )

    contact = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Contact.objects.all(),
        to_field_name="name",
        label="Contact (name or ID)",
    )
    team = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Team.objects.all(),
        to_field_name="name",
        label="Team (name or ID)",
    )

    associated_object_type = ContentTypeFilter()

    class Meta:
        model = ContactAssociation
        fields = "__all__"


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

# Must be imported **after* NautobotFilterSet class is defined to avoid a circular import loop.
from nautobot.tenancy.filters.mixins import TenancyModelFilterSetMixin  # noqa: E402


class DynamicGroupFilterSet(TenancyModelFilterSetMixin, NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "content_type__app_label": "icontains",
            "content_type__model": "icontains",
        },
    )
    content_type = ContentTypeMultipleChoiceFilter(choices=FeatureQuery("dynamic_groups").get_choices, conjoined=False)
    member_id = MultiValueUUIDFilter(
        field_name="static_group_associations__associated_object_id",
        label="Group member ID",
    )

    class Meta:
        model = DynamicGroup
        fields = ("id", "name", "description", "group_type", "tags")


class DynamicGroupMembershipFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "operator": "icontains",
            "group__name": "icontains",
            "parent_group__name": "icontains",
        },
    )
    group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DynamicGroup.objects.all(),
        label="Group (name or ID)",
        to_field_name="name",
    )
    parent_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DynamicGroup.objects.all(),
        label="Parent Group (name or ID)",
        to_field_name="name",
    )

    class Meta:
        model = DynamicGroupMembership
        fields = ("id", "group", "parent_group", "operator", "weight")


class SavedViewFilterSet(BaseFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains", "owner__username": "icontains"})
    owner = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="username",
        queryset=get_user_model().objects.all(),
        label="Owner (ID or name)",
    )

    class Meta:
        model = SavedView
        fields = [
            "id",
            "owner",
            "name",
            "view",
            "is_global_default",
            "is_shared",
        ]


class UserSavedViewAssociationFilterSet(NautobotFilterSet):
    saved_view = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SavedView.objects.all(),
        to_field_name="name",
        label="Saved View (ID or name)",
    )
    user = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="username",
        queryset=get_user_model().objects.all(),
        label="User (ID or username)",
    )

    class Meta:
        model = UserSavedViewAssociation
        fields = ["id", "saved_view", "user", "view_name"]


class StaticGroupAssociationFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "dynamic_group__name": "icontains",
            "dynamic_group__description": "icontains",
            "associated_object_type__app_label": "icontains",
            "associated_object_type__model": "icontains",
        }
    )

    dynamic_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DynamicGroup.objects.all(),
        to_field_name="name",
        label="Dynamic group (name or ID)",
    )
    associated_object_type = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("dynamic_groups").get_choices, conjoined=False
    )

    class Meta:
        model = StaticGroupAssociation
        fields = "__all__"


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
    content_type = ContentTypeFilter()

    class Meta:
        model = ExportTemplate
        fields = ["id", "content_type", "owner_content_type", "owner_object_id", "name"]


#
# External integrations
#


class ExternalIntegrationFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "remote_url": "icontains",
        },
    )
    has_secrets_group = RelatedMembershipBooleanFilter(
        field_name="secrets_group",
        label="Has secrets group",
    )
    secrets_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SecretsGroup.objects.all(),
        label="Secrets group (ID or name)",
    )

    class Meta:
        model = ExternalIntegration
        fields = "__all__"


#
# File proxies
#


class FileProxyFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "job_result__job_model__name": "icontains",
        },
    )
    job = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="job_result__job_model",
        to_field_name="name",
        queryset=Job.objects.all(),
        label="Job (name or ID)",
    )
    job_result_id = django_filters.ModelMultipleChoiceFilter(
        queryset=JobResult.objects.all(),
        label="Job Result (ID)",
    )

    class Meta:
        model = FileProxy
        fields = ["id", "name", "uploaded_at", "job", "job_result_id"]


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
        label="Secrets group (ID or name)",
        to_field_name="name",
    )

    class Meta:
        model = GitRepository
        fields = ["id", "branch", "name", "provided_contents", "remote_url", "slug", "tags"]


#
# GraphQL Queries
#


class GraphQLQueryFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "query": "icontains",
        },
    )

    class Meta:
        model = GraphQLQuery
        fields = [
            "name",
        ]


#
# Image Attachments
#


class ImageAttachmentFilterSet(BaseFilterSet, NameSearchFilterSet):
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
            "grouping": "icontains",
            "description": "icontains",
        },
    )
    job_queues = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=JobQueue.objects.all(),
        label="Job Queue (name or ID)",
    )

    class Meta:
        model = Job
        fields = [
            "id",
            "module_name",
            "job_class_name",
            "name",
            "grouping",
            "installed",
            "enabled",
            "has_sensitive_variables",
            "approval_required",
            "dryrun_default",
            "hidden",
            "read_only",
            "is_job_hook_receiver",
            "is_job_button_receiver",
            "soft_time_limit",
            "time_limit",
            "is_singleton",
            "grouping_override",
            "name_override",
            "approval_required_override",
            "description_override",
            "dryrun_default_override",
            "hidden_override",
            "soft_time_limit_override",
            "time_limit_override",
            "has_sensitive_variables_override",
            "is_singleton_override",
            "tags",
        ]


class JobHookFilterSet(BaseFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains"})
    content_types = ContentTypeMultipleChoiceFilter(
        choices=ChangeLoggedModelsQuery().get_choices,
    )
    job = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Job.objects.all(),
        label="Job (name or ID)",
    )

    class Meta:
        model = JobHook
        fields = [
            "name",
            "content_types",
            "enabled",
            "job",
            "type_create",
            "type_update",
            "type_delete",
        ]


class JobQueueFilterSet(NautobotFilterSet, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "queue_type": "icontains",
            "description": "icontains",
            "tenant__name": "icontains",
        },
    )
    queue_type = django_filters.MultipleChoiceFilter(choices=JobQueueTypeChoices, null_value=None)
    jobs = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Job.objects.all(),
        label="Job (name or ID)",
    )
    has_jobs = RelatedMembershipBooleanFilter(
        field_name="jobs",
        label="Has jobs",
    )

    class Meta:
        model = JobQueue
        fields = [
            "id",
            "name",
            "description",
            "tags",
        ]


class JobQueueAssignmentFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "job__name": "icontains",
            "job__grouping": "icontains",
            "job__description": "icontains",
            "job_queue__name": "icontains",
            "job_queue__description": "icontains",
            "job_queue__queue_type": "icontains",
        }
    )
    job = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Job.objects.all(),
        label="Job (name or ID)",
    )
    job_queue = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=JobQueue.objects.all(),
        label="Job Queue (name or ID)",
    )

    class Meta:
        model = JobQueueAssignment
        fields = ["id"]


class JobResultFilterSet(BaseFilterSet, CustomFieldModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "job_model__name": "icontains",
            "name": "icontains",
            "user__username": "icontains",
            "scheduled_job__name": "icontains",
        },
    )
    job_model = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Job.objects.all(),
        label="Job (name or ID)",
    )
    job_model_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Job.objects.all(),
        label="Job (ID) - Deprecated (use job_model filter)",
    )
    scheduled_job = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=ScheduledJob.objects.all(),
        label="Scheduled Job (name or ID)",
    )
    status = django_filters.MultipleChoiceFilter(choices=JobResultStatusChoices, null_value=None)

    class Meta:
        model = JobResult
        fields = ["id", "date_created", "date_started", "date_done", "name", "status", "user", "scheduled_job"]


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
            "task": "icontains",
            "description": "icontains",
        },
    )
    job_model = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Job.objects.all(),
        label="Job (name or ID)",
    )
    job_model_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Job.objects.all(),
        label="Job (ID) - Deprecated (use job_model filter)",
    )
    time_zone = django_filters.MultipleChoiceFilter(
        choices=[(str(obj), name) for obj, name in TimeZoneField().choices],
        label="Time zone",
        null_value="",
    )

    class Meta:
        model = ScheduledJob
        fields = ["id", "name", "total_run_count", "start_time", "last_run_at", "time_zone"]


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
    job = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Job.objects.all(),
        label="Job (name or ID)",
    )

    class Meta:
        model = JobButton
        fields = (
            "content_types",
            "name",
            "enabled",
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


#
# Metadata
#


class MetadataTypeFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        },
    )
    content_types = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("metadata").get_choices,
    )

    class Meta:
        model = MetadataType
        fields = "__all__"


class MetadataChoiceFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "value": "icontains",
        },
    )

    metadata_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=MetadataType.objects.filter(
            data_type__in=[MetadataTypeDataTypeChoices.TYPE_SELECT, MetadataTypeDataTypeChoices.TYPE_MULTISELECT]
        ),
        label="Metadata type (name or ID)",
    )

    class Meta:
        model = MetadataChoice
        fields = "__all__"


class ObjectMetadataFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "_value": "icontains",
            "metadata_type__name": "icontains",
            "contact__name": "icontains",
            "team__name": "icontains",
        },
    )
    contact = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Contact.objects.all(),
        to_field_name="name",
        label="Contact (name or ID)",
    )
    team = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Team.objects.all(),
        to_field_name="name",
        label="Team (name or ID)",
    )
    metadata_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=MetadataType.objects.all(),
        label="Metadata type (name or ID)",
    )
    assigned_object_type = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("metadata").get_choices,
    )
    value = django_filters.Filter(field_name="_value", method="filter_value")

    class Meta:
        model = ObjectMetadata
        fields = "__all__"

    def filter_value(self, queryset, name, value):
        value = value.strip()
        query = Q(_value__icontains=value)
        if not value:
            return queryset
        return queryset.filter(query)


#
# Notes
#


class NoteFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "user_name": "icontains",
            "note": "icontains",
            "assigned_object_id": {"lookup_expr": "exact", "preprocessor": UUID},
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
            "label": "icontains",
            "description": "icontains",
        }
    )

    source_type = ContentTypeMultipleChoiceFilter(choices=FeatureQuery("relationships").get_choices, conjoined=False)
    destination_type = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("relationships").get_choices, conjoined=False
    )

    class Meta:
        model = Relationship
        fields = ["id", "label", "key", "type", "source_type", "destination_type"]


class RelationshipAssociationFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "relationship__label": "icontains",
            "relationship__key": "icontains",
        }
    )

    relationship = django_filters.ModelMultipleChoiceFilter(
        field_name="relationship__key",
        queryset=Relationship.objects.all(),
        to_field_name="key",
        label="Relationship (key)",
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
        },
    )
    # TODO(Glenn): dynamic choices needed. The issue being that secrets providers are Python
    # classes, not database models.
    # provider = django_filters.MultipleChoiceFilter(choices=..., null_value=None)

    class Meta:
        model = Secret
        fields = ("id", "name", "provider", "created", "last_updated", "tags")


class SecretsGroupFilterSet(
    BaseFilterSet,
    CustomFieldModelFilterSetMixin,
    CreatedUpdatedModelFilterSetMixin,
):
    """Filterset for the SecretsGroup model."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
        },
    )
    secrets = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Secret.objects.all(),
        label="Secret (ID or name)",
        to_field_name="name",
    )

    class Meta:
        model = SecretsGroup
        fields = ("id", "name", "created", "last_updated")


class SecretsGroupAssociationFilterSet(BaseFilterSet):
    """Filterset for the SecretsGroupAssociation through model."""

    q = SearchFilter(
        filter_predicates={
            "secrets_group__name": "icontains",
            "secret__name": "icontains",
        },
    )

    secrets_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SecretsGroup.objects.all(),
        label="Secrets Group (ID or name)",
        to_field_name="name",
    )
    secret_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Secret.objects.all(),
        label="Secret (ID) - Deprecated (use secret filter)",
    )
    secret = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Secret.objects.all(),
        label="Secret (ID or name)",
        to_field_name="name",
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
            "content_types__model": "icontains",
        },
    )
    content_types = ContentTypeMultipleChoiceFilter(
        choices=TaggableClassesQuery().get_choices,
    )

    class Meta:
        model = Tag
        fields = ["id", "name", "color", "content_types"]


#
# Teams
#


class TeamFilterSet(ContactTeamFilterSet):
    class Meta:
        model = Team
        fields = "__all__"


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


class RoleFilterSet(NautobotFilterSet):
    """API filter for filtering custom role object fields."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "content_types__model": "icontains",
        },
    )
    # TODO(timizuo): Add a feature to set conjoined to either True/False from query param in url;
    #  this way only ConfigContext related query would set conjoined to True
    content_types = ContentTypeMultipleChoiceFilter(
        choices=RoleModelsQuery().get_choices,
        # Set the 'conjoined' parameter to False to allow `ConfigContext`
        # to filter the queryset by a combinations of content types,
        # such as 'Device or VirtualMachine' but not 'Device and VirtualMachine'.
        conjoined=False,
    )

    class Meta:
        model = Role
        fields = [
            "id",
            "content_types",
            "color",
            "name",
            "weight",
            "created",
            "last_updated",
        ]
