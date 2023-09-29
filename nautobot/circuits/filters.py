import django_filters
from django.db.models import Q

from nautobot.core.filters import (
    BaseFilterSet,
    NameSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    TreeNodeMultipleChoiceFilter,
)
from nautobot.dcim.filters import (
    CableTerminationModelFilterSetMixin,
    LocatableModelFilterSetMixin,
    PathEndpointModelFilterSetMixin,
)
from nautobot.dcim.models import Location
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
        to_field_name="name",
        label="Provider networks (name or ID)",
    )
    has_provider_networks = RelatedMembershipBooleanFilter(
        field_name="provider_networks",
        label="Has provider networks",
    )
    location = TreeNodeMultipleChoiceFilter(
        field_name="circuits__circuit_terminations__location",
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Location (name or ID)",
    )

    class Meta:
        model = Provider
        fields = [
            "account",
            "admin_contact",
            "asn",
            "comments",
            "id",
            "name",
            "noc_contact",
            "portal_url",
            "tags",
        ]

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
        to_field_name="name",
        label="Provider (name or ID)",
    )

    class Meta:
        model = ProviderNetwork
        fields = ["comments", "description", "id", "name", "tags"]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        # TODO: Remove pylint disable after issue is resolved (see: https://github.com/PyCQA/pylint/issues/7381)
        # pylint: disable=unsupported-binary-operation
        return queryset.filter(
            Q(name__icontains=value) | Q(description__icontains=value) | Q(comments__icontains=value)
        ).distinct()
        # pylint: enable=unsupported-binary-operation


class CircuitTypeFilterSet(NautobotFilterSet, NameSearchFilterSet):
    class Meta:
        model = CircuitType
        fields = ["id", "description", "name"]


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
    provider = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Provider.objects.all(),
        to_field_name="name",
        label="Provider (name or ID)",
    )
    provider_network = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="circuit_terminations__provider_network",
        queryset=ProviderNetwork.objects.all(),
        to_field_name="name",
        label="Provider Network (name or ID)",
    )
    circuit_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=CircuitType.objects.all(),
        to_field_name="name",
        label="Circuit type (name or ID)",
    )
    location = TreeNodeMultipleChoiceFilter(
        field_name="circuit_terminations__location",
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Location (name or ID)",
    )
    has_terminations = RelatedMembershipBooleanFilter(
        field_name="circuit_terminations",
        label="Has terminations",
    )
    circuit_termination_a = django_filters.ModelMultipleChoiceFilter(
        queryset=CircuitTermination.objects.all(),
        label="Termination A (ID)",
    )
    circuit_termination_z = django_filters.ModelMultipleChoiceFilter(
        queryset=CircuitTermination.objects.all(),
        label="Termination Z (ID)",
    )

    class Meta:
        model = Circuit
        fields = [
            "cid",
            "circuit_terminations",
            "comments",
            "commit_rate",
            "description",
            "id",
            "install_date",
            "tags",
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
        to_field_name="name",
        label="Provider Network (name or ID)",
    )

    class Meta:
        model = CircuitTermination
        fields = ["description", "port_speed", "pp_info", "tags", "term_side", "upstream_speed", "xconnect_id"]
