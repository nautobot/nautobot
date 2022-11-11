import django_filters
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters.utils import verbose_lookup_expr
from django.forms import IntegerField

from nautobot.dcim.models import DeviceRedundancyGroup, DeviceRole, DeviceType, Location, Platform, Region, Site
from nautobot.extras.utils import ChangeLoggedModelsQuery, FeatureQuery, TaggableClassesQuery
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.constants import (
    FILTER_CHAR_BASED_LOOKUP_MAP,
    FILTER_NUMERIC_BASED_LOOKUP_MAP,
)
from nautobot.utilities.forms import NullableDateField
from nautobot.utilities.filters import (
    BaseFilterSet,
    ContentTypeFilter,
    ContentTypeMultipleChoiceFilter,
    MultiValueCharFilter,
    MultiValueDateFilter,
    MultiValueNumberFilter,
    MultiValueUUIDFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
    SearchFilter,
    TagFilter,
)
from nautobot.virtualization.models import Cluster, ClusterGroup
from .choices import (
    CustomFieldFilterLogicChoices,
    CustomFieldTypeChoices,
    JobResultStatusChoices,
    RelationshipSideChoices,
    RelationshipTypeChoices,
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
    DynamicGroupMembership,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
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


__all__ = (
    "ComputedFieldFilterSet",
    "ConfigContextFilterSet",
    "ContentTypeFilterSet",
    "CreatedUpdatedFilterSet",
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
    "NautobotFilterSet",
    "NoteFilterSet",
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


# TODO: should be CreatedUpdatedFilterSetMixin.
class CreatedUpdatedFilterSet(django_filters.FilterSet):
    created = django_filters.DateFilter()
    created__gte = django_filters.DateFilter(field_name="created", lookup_expr="gte")
    created__lte = django_filters.DateFilter(field_name="created", lookup_expr="lte")
    last_updated = django_filters.DateTimeFilter()
    last_updated__gte = django_filters.DateTimeFilter(field_name="last_updated", lookup_expr="gte")
    last_updated__lte = django_filters.DateTimeFilter(field_name="last_updated", lookup_expr="lte")


class RelationshipFilter(django_filters.ModelMultipleChoiceFilter):
    """
    Filter objects by the presence of associations on a given Relationship.
    """

    def __init__(self, side, relationship=None, queryset=None, qs=None, *args, **kwargs):
        self.relationship = relationship
        self.qs = qs
        self.side = side
        super().__init__(queryset=queryset, *args, **kwargs)

    def filter(self, qs, value):
        value = [entry.id for entry in value]
        # Check if value is empty or a DynamicChoiceField that is empty.
        if not value or "" in value:
            # if value is empty we return the entire unmodified queryset
            return qs
        else:
            if self.side == "source":
                values = RelationshipAssociation.objects.filter(
                    destination_id__in=value,
                    source_type=self.relationship.source_type,
                    relationship=self.relationship,
                ).values_list("source_id", flat=True)
            elif self.side == "destination":
                values = RelationshipAssociation.objects.filter(
                    source_id__in=value,
                    destination_type=self.relationship.destination_type,
                    relationship=self.relationship,
                ).values_list("destination_id", flat=True)
            else:
                destinations = RelationshipAssociation.objects.filter(
                    source_id__in=value,
                    destination_type=self.relationship.destination_type,
                    relationship=self.relationship,
                ).values_list("destination_id", flat=True)

                sources = RelationshipAssociation.objects.filter(
                    destination_id__in=value,
                    source_type=self.relationship.source_type,
                    relationship=self.relationship,
                ).values_list("source_id", flat=True)

                values = list(destinations) + list(sources)
            qs &= self.get_method(self.qs)(Q(**{"id__in": values}))
            return qs


class RelationshipModelFilterSet(django_filters.FilterSet):
    """
    Filterset for  applicable to the parent model.
    """

    def __init__(self, *args, **kwargs):
        self.obj_type = ContentType.objects.get_for_model(self._meta.model)
        super().__init__(*args, **kwargs)
        self.relationships = []
        self._append_relationships(model=self._meta.model)

    def _append_relationships(self, model):
        """
        Append form fields for all Relationships assigned to this model.
        """
        source_relationships = Relationship.objects.filter(source_type=self.obj_type, source_hidden=False)
        self._append_relationships_side(source_relationships, RelationshipSideChoices.SIDE_SOURCE, model)

        dest_relationships = Relationship.objects.filter(destination_type=self.obj_type, destination_hidden=False)
        self._append_relationships_side(dest_relationships, RelationshipSideChoices.SIDE_DESTINATION, model)

    def _append_relationships_side(self, relationships, initial_side, model):
        """
        Helper method to _append_relationships, for processing one "side" of the relationships for this model.
        """
        for relationship in relationships:
            if relationship.symmetric:
                side = RelationshipSideChoices.SIDE_PEER
            else:
                side = initial_side
            peer_side = RelationshipSideChoices.OPPOSITE[side]

            # If this model is on the "source" side of the relationship, then the field will be named
            # "cr_<relationship-slug>__destination" since it's used to pick the destination object(s).
            # If we're on the "destination" side, the field will be "cr_<relationship-slug>__source".
            # For a symmetric relationship, both sides are "peer", so the field will be "cr_<relationship-slug>__peer"
            field_name = f"cr_{relationship.slug}__{peer_side}"

            if field_name in self.relationships:
                # This is a symmetric relationship that we already processed from the opposing "initial_side".
                # No need to process it a second time!
                continue
            if peer_side == "source":
                choice_model = relationship.source_type.model_class()
            elif peer_side == "destination":
                choice_model = relationship.destination_type.model_class()
            else:
                choice_model = model
            # Check for invalid_relationship unit test
            if choice_model:
                self.filters[field_name] = RelationshipFilter(
                    relationship=relationship,
                    side=side,
                    field_name=field_name,
                    queryset=choice_model.objects.all(),
                    qs=model.objects.all(),
                )
            self.relationships.append(field_name)


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
    location_id = django_filters.ModelMultipleChoiceFilter(
        field_name="locations",
        queryset=Location.objects.all(),
        label="Location (ID)",
    )
    location = django_filters.ModelMultipleChoiceFilter(
        field_name="locations__slug",
        queryset=Location.objects.all(),
        label="Location (slug)",
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


class CustomFieldFilterMixin:
    """
    Filter mixin for CustomField to handle CustomField.filter_logic setting
    and queryset.exclude filtering specific to the JSONField where CustomField data is stored.
    """

    def __init__(self, custom_field, *args, **kwargs):
        self.custom_field = custom_field
        if custom_field.type not in EXACT_FILTER_TYPES:
            if custom_field.filter_logic == CustomFieldFilterLogicChoices.FILTER_LOOSE:
                kwargs.setdefault("lookup_expr", "icontains")
        super().__init__(*args, **kwargs)
        self.field_name = f"_custom_field_data__{self.field_name}"

    def filter(self, qs, value):
        if value in django_filters.constants.EMPTY_VALUES:
            return qs

        if value == "null":
            return self.get_method(qs)(
                Q(**{f"{self.field_name}__exact": None}) | Q(**{f"{self.field_name}__isnull": True})
            )

        # Custom fields require special handling for exclude filtering.
        # Return custom fields that don't match the value and null custom fields
        if self.exclude:
            qs_null_custom_fields = qs.filter(**{f"{self.field_name}__isnull": True}).distinct()
            return super().filter(qs, value) | qs_null_custom_fields

        return super().filter(qs, value)


class CustomFieldBooleanFilter(CustomFieldFilterMixin, django_filters.BooleanFilter):
    """Custom field single value filter for backwards compatibility"""


class CustomFieldCharFilter(CustomFieldFilterMixin, django_filters.Filter):
    """Custom field single value filter for backwards compatibility"""


class CustomFieldDateFilter(CustomFieldFilterMixin, django_filters.DateFilter):
    """Custom field single value filter for backwards compatibility"""

    field_class = NullableDateField


class CustomFieldJSONFilter(CustomFieldFilterMixin, django_filters.Filter):
    """Custom field single value filter for backwards compatibility"""


class CustomFieldMultiSelectFilter(CustomFieldFilterMixin, django_filters.Filter):
    """Custom field single value filter for backwards compatibility"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("lookup_expr", "contains")
        super().__init__(*args, **kwargs)


class CustomFieldNumberFilter(CustomFieldFilterMixin, django_filters.Filter):
    """Custom field single value filter for backwards compatibility"""

    field_class = IntegerField


class CustomFieldMultiValueCharFilter(CustomFieldFilterMixin, MultiValueCharFilter):
    """Custom field multi value char filter for extended lookup expressions"""


class CustomFieldMultiValueDateFilter(CustomFieldFilterMixin, MultiValueDateFilter):
    """Custom field multi value date filter for extended lookup expressions"""


class CustomFieldMultiValueNumberFilter(CustomFieldFilterMixin, MultiValueNumberFilter):
    """Custom field multi value number filter for extended lookup expressions"""


# TODO: should be CustomFieldModelFilterSetMixin
class CustomFieldModelFilterSet(django_filters.FilterSet):
    """
    Dynamically add a Filter for each CustomField applicable to the parent model. Add filters for
    extra lookup expressions on supported CustomField types.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        custom_field_filter_classes = {
            CustomFieldTypeChoices.TYPE_DATE: CustomFieldDateFilter,
            CustomFieldTypeChoices.TYPE_BOOLEAN: CustomFieldBooleanFilter,
            CustomFieldTypeChoices.TYPE_INTEGER: CustomFieldNumberFilter,
            CustomFieldTypeChoices.TYPE_JSON: CustomFieldJSONFilter,
            CustomFieldTypeChoices.TYPE_MULTISELECT: CustomFieldMultiSelectFilter,
        }

        custom_fields = CustomField.objects.filter(
            content_types=ContentType.objects.get_for_model(self._meta.model)
        ).exclude(filter_logic=CustomFieldFilterLogicChoices.FILTER_DISABLED)
        for cf in custom_fields:
            # Determine filter class for this CustomField type, default to CustomFieldBaseFilter
            # 2.0 TODO: #824 use cf.slug instead
            new_filter_name = f"cf_{cf.name}"
            filter_class = custom_field_filter_classes.get(cf.type, CustomFieldCharFilter)
            new_filter_field = filter_class(field_name=cf.name, custom_field=cf)
            new_filter_field.label = f"{cf.label}"

            # Create base filter (cf_customfieldname)
            self.filters[new_filter_name] = new_filter_field

            # Create extra lookup expression filters (cf_customfieldname__lookup_expr)
            self.filters.update(
                self._generate_custom_field_lookup_expression_filters(filter_name=new_filter_name, custom_field=cf)
            )

    @staticmethod
    def _get_custom_field_filter_lookup_dict(filter_type):
        # Choose the lookup expression map based on the filter type
        if issubclass(filter_type, (CustomFieldMultiValueNumberFilter, CustomFieldMultiValueDateFilter)):
            lookup_map = FILTER_NUMERIC_BASED_LOOKUP_MAP
        else:
            lookup_map = FILTER_CHAR_BASED_LOOKUP_MAP

        return lookup_map

    # TODO 2.0: Transition CustomField filters to nautobot.utilities.filters.MultiValue* filters and
    # leverage BaseFilterSet to add dynamic lookup expression filters. Remove CustomField.filter_logic field
    @classmethod
    def _generate_custom_field_lookup_expression_filters(cls, filter_name, custom_field):
        """
        For specific filter types, new filters are created based on defined lookup expressions in
        the form `<field_name>__<lookup_expr>`. Copied from nautobot.utilities.filters.BaseFilterSet
        and updated to work with custom fields.
        """
        magic_filters = {}
        custom_field_type_to_filter_map = {
            CustomFieldTypeChoices.TYPE_DATE: CustomFieldMultiValueDateFilter,
            CustomFieldTypeChoices.TYPE_INTEGER: CustomFieldMultiValueNumberFilter,
            CustomFieldTypeChoices.TYPE_SELECT: CustomFieldMultiValueCharFilter,
            CustomFieldTypeChoices.TYPE_TEXT: CustomFieldMultiValueCharFilter,
            CustomFieldTypeChoices.TYPE_URL: CustomFieldMultiValueCharFilter,
        }

        if custom_field.type in custom_field_type_to_filter_map:
            filter_type = custom_field_type_to_filter_map[custom_field.type]
        else:
            return magic_filters

        # Choose the lookup expression map based on the filter type
        lookup_map = cls._get_custom_field_filter_lookup_dict(filter_type)

        # Create new filters for each lookup expression in the map
        for lookup_name, lookup_expr in lookup_map.items():
            new_filter_name = f"{filter_name}__{lookup_name}"
            new_filter = filter_type(
                field_name=custom_field.name,
                lookup_expr=lookup_expr,
                custom_field=custom_field,
                label=f"{custom_field.label} ({verbose_lookup_expr(lookup_expr)})",
                exclude=lookup_name.startswith("n"),
            )

            magic_filters[new_filter_name] = new_filter

        return magic_filters


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


class NautobotFilterSet(BaseFilterSet, CreatedUpdatedFilterSet, RelationshipModelFilterSet, CustomFieldModelFilterSet):
    """
    This class exists to combine common functionality and is used as a base class throughout the
    codebase where all of BaseFilterSet, CreatedUpdatedFilterSet, RelationshipModelFilterSet and CustomFieldModelFilterSet
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
            "has_sensitive_variables",
            "approval_required",
            "commit_default",
            "hidden",
            "read_only",
            "is_job_hook_receiver",
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


# TODO: should be LocalContextFilterSetMixin
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
        # Sometimes the incoming value is an instance. This block of logic comes from the base
        # `get_filter_predicate()` and was added here to support this.
        try:
            return {name: getattr(value, to_field_name)}
        except (AttributeError, TypeError):
            return {name: value}


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
