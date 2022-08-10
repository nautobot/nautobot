import django_filters

from nautobot.dcim.models import Location
from nautobot.extras.filters import NautobotFilterSet
from nautobot.utilities.filters import (
    NameSlugSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    TagFilter,
    TreeNodeMultipleChoiceFilter,
)
from .models import Tenant, TenantGroup


__all__ = (
    "TenancyFilterSet",
    "TenantFilterSet",
    "TenantGroupFilterSet",
)


class TenantGroupFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    parent_id = django_filters.ModelMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        label="Tenant group (ID)",
    )
    parent = django_filters.ModelMultipleChoiceFilter(
        field_name="parent__slug",
        queryset=TenantGroup.objects.all(),
        to_field_name="slug",
        label="Tenant group group (slug)",
    )

    class Meta:
        model = TenantGroup
        fields = ["id", "name", "slug", "description"]


class TenantFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "slug": "icontains",
            "description": "icontains",
            "comments": "icontains",
        },
    )
    group_id = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="group",
        label="Tenant group (ID)",
    )
    group = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="group",
        to_field_name="slug",
        label="Tenant group (slug)",
    )
    locations = TreeNodeMultipleChoiceFilter(
        queryset=Location.objects.all(),
        label="Locations (slugs and/or IDs)",
    )
    has_locations = RelatedMembershipBooleanFilter(
        field_name="locations",
        label="Has locations",
    )
    tag = TagFilter()

    class Meta:
        model = Tenant
        fields = ["id", "name", "slug"]


# TODO: should be TenancyFilterSetMixin
class TenancyFilterSet(django_filters.FilterSet):
    """
    An inheritable FilterSet for models which support Tenant assignment.
    """

    tenant_group_id = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="tenant__group",
        label="Tenant Group (ID)",
    )
    tenant_group = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="tenant__group",
        to_field_name="slug",
        label="Tenant Group (slug)",
    )
    tenant_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        label='Tenant (ID) (deprecated, use "tenant" filter instead)',
    )
    tenant = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        label="Tenant (slug or ID)",
    )
