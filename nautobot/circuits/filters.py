import django_filters
from django.db.models import Q

from nautobot.dcim.filters import (
    CableTerminationModelFilterSetMixin,
    LocatableModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
)
from nautobot.dcim.models import Location, Region, Site
from nautobot.extras.filters import NautobotFilterSet, StatusModelFilterSetMixin
from nautobot.tenancy.filters import TenancyModelFilterSetMixin
from nautobot.utilities.filters import (
    BaseFilterSet,
    NameSlugSearchFilterSet,
    SearchFilter,
    TagFilter,
    TreeNodeMultipleChoiceFilter,
)
from .models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork

__all__ = (
    "CircuitFilterSet",
    "CircuitTerminationFilterSet",
    "CircuitTypeFilterSet",
    "ProviderFilterSet",
    "ProviderNetworkFilterSet",
)


class ProviderFilterSet(NautobotFilterSet):
    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="circuits__terminations__site__region",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="circuits__terminations__site__region",
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
    location = TreeNodeMultipleChoiceFilter(
        field_name="circuits__terminations__location__slug",
        queryset=Location.objects.all(),
        to_field_name="slug",
        label="Location (slug or ID)",
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


class ProviderNetworkFilterSet(NautobotFilterSet):
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
    tag = TagFilter()

    class Meta:
        model = ProviderNetwork
        fields = ["id", "name", "slug"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(description__icontains=value) | Q(comments__icontains=value)
        ).distinct()


class CircuitTypeFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    class Meta:
        model = CircuitType
        fields = ["id", "name", "slug"]


class CircuitFilterSet(NautobotFilterSet, StatusModelFilterSetMixin, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "cid": "icontains",
            "terminations__xconnect_id": "icontains",
            "terminations__pp_info": "icontains",
            "terminations__description": "icontains",
            "description": "icontains",
            "comments": "icontains",
        },
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
    provider_network_id = django_filters.ModelMultipleChoiceFilter(
        field_name="terminations__provider_network",
        queryset=ProviderNetwork.objects.all(),
        label="Provider Network (ID)",
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
    location = TreeNodeMultipleChoiceFilter(
        field_name="terminations__location__slug",
        queryset=Location.objects.all(),
        to_field_name="slug",
        label="Location (slug or ID)",
    )
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="terminations__site__region",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="terminations__site__region",
        to_field_name="slug",
        label="Region (slug)",
    )
    tag = TagFilter()

    class Meta:
        model = Circuit
        fields = ["id", "cid", "install_date", "commit_rate"]


class CircuitTerminationFilterSet(
    BaseFilterSet,
    CableTerminationModelFilterSetMixin,
    LocatableModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
):
    q = SearchFilter(
        filter_predicates={
            "circuit__cid": "icontains",
            "xconnect_id": "icontains",
            "pp_info": "icontains",
            "description": "icontains",
        },
    )
    circuit_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Circuit.objects.all(),
        label="Circuit",
    )
    provider_network_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ProviderNetwork.objects.all(),
        label="Provider Network (ID)",
    )

    class Meta:
        model = CircuitTermination
        fields = ["term_side", "port_speed", "upstream_speed", "xconnect_id"]
