import django_filters
from django.db.models import Q

from nautobot.dcim.filters import CableTerminationFilterSet, PathEndpointFilterSet
from nautobot.dcim.models import Region, Site
from nautobot.extras.filters import (
    CustomFieldModelFilterSet,
    CreatedUpdatedFilterSet,
    StatusModelFilterSetMixin,
)
from nautobot.tenancy.filters import TenancyFilterSet
from nautobot.utilities.filters import (
    BaseFilterSet,
    NameSlugSearchFilterSet,
    TagFilter,
    TreeNodeMultipleChoiceFilter,
)
from .models import Circuit, CircuitTermination, CircuitType, Provider

__all__ = (
    "CircuitFilterSet",
    "CircuitTerminationFilterSet",
    "CircuitTypeFilterSet",
    "ProviderFilterSet",
)


class ProviderFilterSet(BaseFilterSet, CustomFieldModelFilterSet, CreatedUpdatedFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="circuits__terminations__site__region",
        lookup_expr="in",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="circuits__terminations__site__region",
        lookup_expr="in",
        to_field_name="slug",
        label="Region (slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="circuits__terminations__site",
        queryset=Site.objects.all(),
        label="Site",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="circuits__terminations__site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site (slug)",
    )
    tag = TagFilter()

    class Meta:
        model = Provider
        fields = ["id", "name", "slug", "asn", "account"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(account__icontains=value)
            | Q(noc_contact__icontains=value)
            | Q(admin_contact__icontains=value)
            | Q(comments__icontains=value)
        )


class CircuitTypeFilterSet(
    BaseFilterSet,
    CustomFieldModelFilterSet,
    NameSlugSearchFilterSet,
    CreatedUpdatedFilterSet,
):
    class Meta:
        model = CircuitType
        fields = ["id", "name", "slug"]


class CircuitFilterSet(
    BaseFilterSet,
    StatusModelFilterSetMixin,
    CustomFieldModelFilterSet,
    TenancyFilterSet,
    CreatedUpdatedFilterSet,
):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    provider_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Provider.objects.all(),
        label="Provider (ID)",
    )
    provider = django_filters.ModelMultipleChoiceFilter(
        field_name="provider__slug",
        queryset=Provider.objects.all(),
        to_field_name="slug",
        label="Provider (slug)",
    )
    type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=CircuitType.objects.all(),
        label="Circuit type (ID)",
    )
    type = django_filters.ModelMultipleChoiceFilter(
        field_name="type__slug",
        queryset=CircuitType.objects.all(),
        to_field_name="slug",
        label="Circuit type (slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="terminations__site",
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="terminations__site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site (slug)",
    )
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="terminations__site__region",
        lookup_expr="in",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="terminations__site__region",
        lookup_expr="in",
        to_field_name="slug",
        label="Region (slug)",
    )
    tag = TagFilter()

    class Meta:
        model = Circuit
        fields = ["id", "cid", "install_date", "commit_rate"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(cid__icontains=value)
            | Q(terminations__xconnect_id__icontains=value)
            | Q(terminations__pp_info__icontains=value)
            | Q(terminations__description__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        ).distinct()


class CircuitTerminationFilterSet(BaseFilterSet, CableTerminationFilterSet, PathEndpointFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    circuit_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Circuit.objects.all(),
        label="Circuit",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site (slug)",
    )

    class Meta:
        model = CircuitTermination
        fields = ["term_side", "port_speed", "upstream_speed", "xconnect_id"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(circuit__cid__icontains=value)
            | Q(xconnect_id__icontains=value)
            | Q(pp_info__icontains=value)
            | Q(description__icontains=value)
        ).distinct()
