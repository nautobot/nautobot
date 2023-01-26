import django_filters
from django.db.models import Q

from nautobot.core.filters import (
    BaseFilterSet,
    NameSlugSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    SearchFilter,
    TagFilter,
    TreeNodeMultipleChoiceFilter,
)
from nautobot.dcim.filters import (
    CableTerminationModelFilterSetMixin,
    LocatableModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
)
from nautobot.dcim.models import Location, Region, Site
from nautobot.extras.filters import NautobotFilterSet, StatusModelFilterSetMixin
from nautobot.tenancy.filters import TenancyModelFilterSetMixin
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
        field_name="circuits__circuit_terminations__site__region",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="circuits__circuit_terminations__site__region",
        to_field_name="slug",
        label="Region (slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="circuits__circuit_terminations__site",
        queryset=Site.objects.all(),
        label="Site",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="circuits__circuit_terminations__site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site (slug)",
    )
    location = TreeNodeMultipleChoiceFilter(
        field_name="circuits__circuit_terminations__location__slug",
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
        # TODO: Remove pylint disable after issue is resolved (see: https://github.com/PyCQA/pylint/issues/7381)
        # pylint: disable=unsupported-binary-operation
        return queryset.filter(
            Q(name__icontains=value)
            | Q(account__icontains=value)
            | Q(noc_contact__icontains=value)
            | Q(admin_contact__icontains=value)
            | Q(comments__icontains=value)
        )
        # pylint: enable=unsupported-binary-operation


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
        # TODO: Remove pylint disable after issue is resolved (see: https://github.com/PyCQA/pylint/issues/7381)
        # pylint: disable=unsupported-binary-operation
        return queryset.filter(
            Q(name__icontains=value) | Q(description__icontains=value) | Q(comments__icontains=value)
        ).distinct()
        # pylint: enable=unsupported-binary-operation


class CircuitTypeFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    class Meta:
        model = CircuitType
        fields = ["id", "name", "slug"]


class CircuitFilterSet(NautobotFilterSet, StatusModelFilterSetMixin, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "cid": "icontains",
            "circuit_terminations__xconnect_id": "icontains",
            "circuit_terminations__pp_info": "icontains",
            "circuit_terminations__description": "icontains",
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
        field_name="circuit_terminations__provider_network",
        queryset=ProviderNetwork.objects.all(),
        label="Provider Network (ID)",
    )
    circuit_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=CircuitType.objects.all(),
        to_field_name="slug",
        label="Circuit type (slug or ID)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="circuit_terminations__site",
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="circuit_terminations__site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site (slug)",
    )
    location = TreeNodeMultipleChoiceFilter(
        field_name="circuit_terminations__location__slug",
        queryset=Location.objects.all(),
        to_field_name="slug",
        label="Location (slug or ID)",
    )
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="circuit_terminations__site__region",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="circuit_terminations__site__region",
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
