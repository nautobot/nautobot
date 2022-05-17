import django_filters

from nautobot.extras.filters import NautobotFilterSet
from nautobot.utilities.filters import (
    NameSlugSearchFilterSet,
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
        lookup_expr="in",
        label="Tenant group (ID)",
    )
    group = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="group",
        lookup_expr="in",
        to_field_name="slug",
        label="Tenant group (slug)",
    )
    tag = TagFilter()

    class Meta:
        model = Tenant
        fields = ["id", "name", "slug"]


class TenancyFilterSet(django_filters.FilterSet):
    """
    An inheritable FilterSet for models which support Tenant assignment.
    """

    tenant_group_id = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="tenant__group",
        lookup_expr="in",
        label="Tenant Group (ID)",
    )
    tenant_group = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="tenant__group",
        to_field_name="slug",
        lookup_expr="in",
        label="Tenant Group (slug)",
    )
    tenant_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        label="Tenant (ID)",
    )
    tenant = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        field_name="tenant__slug",
        to_field_name="slug",
        label="Tenant (slug)",
    )
