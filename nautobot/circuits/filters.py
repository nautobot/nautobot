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
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
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
    circuits = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="cid",
        queryset=Circuit.objects.all(),
        label="Circuit (ID or circuit ID)",
    )
    has_circuits = RelatedMembershipBooleanFilter(
        field_name="circuits",
        label="Has circuits",
    )
    provider_networks = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ProviderNetwork.objects.all(),
        label="Provider networks (slug or ID)",
    )
    has_provider_networks = RelatedMembershipBooleanFilter(
        field_name="provider_networks",
        label="Has provider networks",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="circuits__terminations__site__region",
        label="Region (slug or ID)",
    )
    site = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="circuits__terminations__site",
        queryset=Site.objects.all(),
        label="Site (slug or ID)",
    )
    location = TreeNodeMultipleChoiceFilter(
        field_name="circuits__terminations__location",
        queryset=Location.objects.all(),
        label="Location (slug or ID)",
    )
    tags = TagFilter()

    class Meta:
        model = Provider
        fields = ["account", "admin_contact", "asn", "comments", "id", "name", "noc_contact", "portal_url", "slug"]

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
    circuit_terminations = django_filters.ModelMultipleChoiceFilter(
        queryset=CircuitTermination.objects.all(),
        label="Circuit Terminations (ID)",
    )
    has_circuit_terminations = RelatedMembershipBooleanFilter(
        field_name="circuit_terminations",
        label="Has circuit terminations",
    )
    provider = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="provider",
        queryset=Provider.objects.all(),
        label="Provider (slug or ID)",
    )
    tags = TagFilter()

    class Meta:
        model = ProviderNetwork
        fields = ["comments", "description", "id", "name", "slug"]

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
        fields = ["id", "description", "name", "slug"]


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
    provider = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Provider.objects.all(),
        label="Provider (slug or ID)",
    )
    provider_network = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="terminations__provider_network",
        queryset=ProviderNetwork.objects.all(),
        label="Provider Network (slug or ID)",
    )
    type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=CircuitType.objects.all(),
        label="Circuit type (slug or ID)",
    )
    site = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="terminations__site",
        queryset=Site.objects.all(),
        label="Site (slug or ID)",
    )
    location = TreeNodeMultipleChoiceFilter(
        field_name="terminations__location",
        queryset=Location.objects.all(),
        label="Location (slug or ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="terminations__site__region",
        label="Region (slug or ID)",
    )
    has_terminations = RelatedMembershipBooleanFilter(
        field_name="terminations",
        label="Has terminations",
    )
    termination_a = django_filters.ModelMultipleChoiceFilter(
        queryset=CircuitTermination.objects.all(),
        label="Termination A (ID)",
    )
    termination_z = django_filters.ModelMultipleChoiceFilter(
        queryset=CircuitTermination.objects.all(),
        label="Termination Z (ID)",
    )
    tags = TagFilter()

    class Meta:
        model = Circuit
        fields = [
            "cid",
            "comments",
            "commit_rate",
            "description",
            "id",
            "install_date",
            "terminations",
        ]


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
    circuit = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="cid",
        queryset=Circuit.objects.all(),
        label="Circuit (ID or circuit ID)",
    )
    provider_network = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ProviderNetwork.objects.all(),
        label="Provider Network (ID or slug)",
    )

    class Meta:
        model = CircuitTermination
        fields = ["description", "port_speed", "pp_info", "term_side", "upstream_speed", "xconnect_id"]
