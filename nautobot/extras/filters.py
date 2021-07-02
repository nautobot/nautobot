import django_filters
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.forms import DateField, IntegerField, NullBooleanField

from nautobot.dcim.models import DeviceRole, DeviceType, Platform, Region, Site
from nautobot.extras.utils import FeatureQuery
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.filters import (
    BaseFilterSet,
    ContentTypeFilter,
    ContentTypeMultipleChoiceFilter,
    TagFilter,
)
from nautobot.virtualization.models import Cluster, ClusterGroup
from .choices import *
from .models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    JobResult,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    Status,
    Tag,
    Webhook,
)


__all__ = (
    "ConfigContextFilterSet",
    "ContentTypeFilterSet",
    "CreatedUpdatedFilterSet",
    "CustomFieldFilter",
    "CustomFieldModelFilterSet",
    "CustomLinkFilterSet",
    "ExportTemplateFilterSet",
    "GitRepositoryFilterSet",
    "GraphQLQueryFilterSet",
    "ImageAttachmentFilterSet",
    "JobResultFilterSet",
    "LocalContextFilterSet",
    "ObjectChangeFilterSet",
    "RelationshipFilterSet",
    "RelationshipAssociationFilterSet",
    "StatusFilter",
    "StatusFilterSet",
    "StatusModelFilterSetMixin",
    "TagFilterSet",
    "WebhookFilterSet",
)

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
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    content_types = ContentTypeMultipleChoiceFilter(
        choices=FeatureQuery("custom_fields").get_choices,
    )

    class Meta:
        model = CustomField
        fields = ["id", "content_types", "name", "required", "filter_logic", "weight"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(label__icontains=value))


class CustomFieldChoiceFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
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

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(value__icontains=value))


class ExportTemplateFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    owner_content_type = ContentTypeFilter()

    class Meta:
        model = ExportTemplate
        fields = ["id", "content_type", "owner_content_type", "owner_object_id", "name"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(owner_content_type__app_label__icontains=value)
            | Q(owner_content_type__model__icontains=value)
            | Q(content_type__app_label__icontains=value)
            | Q(content_type__model__icontains=value)
            | Q(description__icontains=value)
        )


class ImageAttachmentFilterSet(BaseFilterSet):
    content_type = ContentTypeFilter()

    class Meta:
        model = ImageAttachment
        fields = ["id", "content_type_id", "object_id", "name"]


class ConfigContextFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
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

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value) | Q(data__icontains=value))


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


#
# Filter for config context schema
#


class ConfigContextSchemaFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    owner_content_type = ContentTypeFilter()

    class Meta:
        model = ConfigContextSchema
        fields = [
            "id",
            "name",
            "description",
        ]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(description__icontains=value) | Q(data_schema__icontains=value)
        )


class ObjectChangeFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    time = django_filters.DateTimeFromToRangeFilter()
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
        ]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(user_name__icontains=value) | Q(object_repr__icontains=value))


class CreatedUpdatedFilterSet(django_filters.FilterSet):
    created = django_filters.DateFilter()
    created__gte = django_filters.DateFilter(field_name="created", lookup_expr="gte")
    created__lte = django_filters.DateFilter(field_name="created", lookup_expr="lte")
    last_updated = django_filters.DateTimeFilter()
    last_updated__gte = django_filters.DateTimeFilter(field_name="last_updated", lookup_expr="gte")
    last_updated__lte = django_filters.DateTimeFilter(field_name="last_updated", lookup_expr="lte")


#
# Job Results
#


class JobResultFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    obj_type = ContentTypeFilter()
    created = django_filters.DateTimeFilter()
    completed = django_filters.DateTimeFilter()
    status = django_filters.MultipleChoiceFilter(choices=JobResultStatusChoices, null_value=None)

    class Meta:
        model = JobResult
        fields = ["id", "created", "completed", "status", "user", "obj_type", "name"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(user__username__icontains=value))


#
# ContentTypes
#


class ContentTypeFilterSet(django_filters.FilterSet):
    class Meta:
        model = ContentType
        fields = ["id", "app_label", "model"]


#
# Tags
#


class TagFilterSet(BaseFilterSet, CreatedUpdatedFilterSet, CustomFieldModelFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "color"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(slug__icontains=value))


#
# Datasources
#


class GitRepositoryFilterSet(BaseFilterSet, CreatedUpdatedFilterSet, CustomFieldModelFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    tag = TagFilter()

    class Meta:
        model = GitRepository
        fields = ["id", "name", "slug", "remote_url", "branch"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        qs_filter = Q(name__icontains=value) | Q(remote_url__icontains=value) | Q(branch__icontains=value)
        try:
            qs_filter |= Q(asn=int(value.strip()))
        except ValueError:
            pass
        return queryset.filter(qs_filter)


#
# Custom Links
#


class CustomLinkFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
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

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(target_url__icontains=value)
            | Q(text__icontains=value)
            | Q(content_type__app_label__icontains=value)
            | Q(content_type__model__icontains=value)
        )


#
# Webhooks
#


class WebhookFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
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

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(payload_url__icontains=value)
            | Q(additional_headers__icontains=value)
            | Q(body_template__icontains=value)
        )


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


class StatusFilterSet(BaseFilterSet, CreatedUpdatedFilterSet, CustomFieldModelFilterSet):
    """API filter for filtering custom status object fields."""

    q = django_filters.CharFilter(
        method="search",
        label="Search",
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

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(slug__icontains=value) | Q(content_types__model__icontains=value)
        ).distinct()


class StatusModelFilterSetMixin(django_filters.FilterSet):
    """
    Mixin to add a `status` filter field to a FilterSet.
    """

    status = StatusFilter()


#
# Relationship
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


class GraphQLQueryFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    class Meta:
        model = GraphQLQuery
        fields = (
            "name",
            "slug",
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(slug__icontains=value) | Q(query__icontains=value))


class ComputedFieldFilterSet(BaseFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
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

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(target_url__icontains=value)
            | Q(text__icontains=value)
            | Q(content_type__app_label__icontains=value)
            | Q(content_type__model__icontains=value)
        )
