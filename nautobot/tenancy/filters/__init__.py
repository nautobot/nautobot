import django_filters

from nautobot.dcim.models import Location
from nautobot.extras.filters import NautobotFilterSet
from nautobot.tenancy.filters.mixins import TenancyModelFilterSetMixin
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.deprecation import class_deprecated_in_favor_of
from nautobot.utilities.filters import (
    NameSlugSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    TagFilter,
    TreeNodeMultipleChoiceFilter,
)


__all__ = (
    "TenancyFilterSet",
    "TenancyModelFilterSetMixin",
    "TenantFilterSet",
    "TenantGroupFilterSet",
)


class TenantGroupFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    parent_id = django_filters.ModelMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        label="Tenant group (ID) - Deprecated (use parent filter)",
    )
    parent = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        label="Tenant group group (ID or slug)",
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


# TODO: remove in 2.2
@class_deprecated_in_favor_of(TenancyModelFilterSetMixin)
class TenancyFilterSet(TenancyModelFilterSetMixin):
    pass
