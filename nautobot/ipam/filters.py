import contextlib
import uuid

from django.core.exceptions import ValidationError
from django.db.models import Q
import django_filters
import netaddr

from nautobot.cloud.models import CloudNetwork
from nautobot.core.filters import (
    ModelMultipleChoiceFilter,
    MultiValueCharFilter,
    MultiValueNumberFilter,
    MultiValueUUIDFilter,
    NameSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    NumericArrayFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    TreeNodeMultipleChoiceFilter,
)
from nautobot.core.utils.data import is_uuid
from nautobot.dcim.filters import LocatableModelFilterSetMixin
from nautobot.dcim.models import Device, Interface, Location, VirtualDeviceContext
from nautobot.extras.filters import NautobotFilterSet, RoleModelFilterSetMixin, StatusModelFilterSetMixin
from nautobot.ipam import choices
from nautobot.ipam.filter_mixins import PrefixFilter
from nautobot.tenancy.filter_mixins import TenancyModelFilterSetMixin
from nautobot.virtualization.models import VirtualMachine, VMInterface
from nautobot.vpn.models import VPNTunnelEndpoint

from .models import (
    IPAddress,
    IPAddressToInterface,
    Namespace,
    Prefix,
    PrefixLocationAssignment,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VLANLocationAssignment,
    VRF,
    VRFDeviceAssignment,
    VRFPrefixAssignment,
)

__all__ = (
    "IPAddressFilterSet",
    "NamespaceFilterSet",
    "PrefixFilter",
    "PrefixFilterSet",
    "RIRFilterSet",
    "RouteTargetFilterSet",
    "ServiceFilterSet",
    "VLANFilterSet",
    "VLANGroupFilterSet",
    "VRFFilterSet",
)


class NamespaceFilterSet(NautobotFilterSet, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
        },
    )

    class Meta:
        model = Namespace
        fields = "__all__"


class VRFFilterSet(NautobotFilterSet, StatusModelFilterSetMixin, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "rd": "icontains",
            "description": "icontains",
        },
    )
    import_targets = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=RouteTarget.objects.all(),
        to_field_name="name",
    )
    export_targets = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=RouteTarget.objects.all(),
        to_field_name="name",
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="devices",
        queryset=Device.objects.all(),
        to_field_name="name",
    )
    virtual_machines = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualMachine.objects.all(),
        to_field_name="name",
    )
    prefix = PrefixFilter(field_name="prefixes")
    namespace = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Namespace.objects.all(),
        to_field_name="name",
    )
    virtual_device_contexts = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualDeviceContext.objects.all(),
        to_field_name="name",
    )

    class Meta:
        model = VRF
        fields = ["id", "name", "rd", "tags", "description"]


class VRFDeviceAssignmentFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "vrf__name": "icontains",
            "device__name": "icontains",
            "virtual_machine__name": "icontains",
            "virtual_device_context__name": "icontains",
            "rd": "icontains",
        },
    )
    vrf = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VRF.objects.all(),
        to_field_name="name",
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
    )
    virtual_machine = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualMachine.objects.all(),
        to_field_name="name",
    )
    virtual_device_context = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualDeviceContext.objects.all(),
        to_field_name="name",
    )

    class Meta:
        model = VRFDeviceAssignment
        fields = ["id", "name", "rd"]


class VRFPrefixAssignmentFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            # "prefix__prefix": "iexact",  # TODO?
            "vrf__name": "icontains",
        },
    )
    prefix = PrefixFilter()
    vrf = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VRF.objects.all(),
        to_field_name="name",
    )

    class Meta:
        model = VRFPrefixAssignment
        fields = ["id", "vrf", "prefix"]


class RouteTargetFilterSet(NautobotFilterSet, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        },
    )
    importing_vrfs = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="Import VRF(s) (ID or RD)",
    )
    exporting_vrfs = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="Export VRF(s) (ID or RD)",
    )

    class Meta:
        model = RouteTarget
        fields = ["id", "name", "tags"]


class RIRFilterSet(NautobotFilterSet, NameSearchFilterSet):
    class Meta:
        model = RIR
        fields = ["id", "name", "is_private", "description"]


class IPAMFilterSetMixin(django_filters.FilterSet):
    """Filterset mixin to add shared filters across all IPAM objects."""

    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    def search(self, qs, name, value):
        value = value.strip()

        if not value:
            return qs

        return qs.string_search(value)


class PrefixFilterSet(
    NautobotFilterSet,
    IPAMFilterSetMixin,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
):
    parent = PrefixFilter()
    prefix = MultiValueCharFilter(
        method="filter_prefix",
        label="Prefix",
    )
    within = MultiValueCharFilter(
        method="search_within",
        label="Within prefix",
    )
    within_include = MultiValueCharFilter(
        method="search_within_include",
        label="Within and including prefix",
    )
    contains = MultiValueCharFilter(
        method="search_contains",
        label="Prefixes which contain this prefix or IP",
    )
    ancestors = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Prefix.objects.all(),
        prefers_id=True,
        to_field_name="network",
        method="filter_ancestors",
        label="Prefixes which are ancestors of this prefix (ID or host string)",
    )
    vrfs = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="Assigned VRF (ID or RD)",
    )
    # TODO: change to a multiple-value filter as a breaking change for dynamic groups and permissions definition
    present_in_vrf_id = django_filters.ModelChoiceFilter(
        field_name="vrfs",
        queryset=VRF.objects.all(),
        method="filter_present_in_vrf",
        label="Present in VRF",
    )
    # TODO: change to a multiple-value filter as a breaking change for dynamic groups and permissions definition
    present_in_vrf = django_filters.ModelChoiceFilter(
        field_name="vrfs__rd",
        queryset=VRF.objects.all(),
        method="filter_present_in_vrf",
        to_field_name="rd",
        label="Present in VRF (RD)",
    )
    vlan_id = ModelMultipleChoiceFilter(
        queryset=VLAN.objects.all(),
    )
    vlan_vid = MultiValueNumberFilter(
        field_name="vlan__vid",
        label="VLAN number (1-4095)",
    )
    rir = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=RIR.objects.all(),
        to_field_name="name",
    )
    has_rir = RelatedMembershipBooleanFilter(
        field_name="rir",
        label="Has RIR",
    )
    type = django_filters.MultipleChoiceFilter(choices=choices.PrefixTypeChoices)
    namespace = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Namespace.objects.all(),
        to_field_name="name",
    )
    ip_version = django_filters.NumberFilter()
    location = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        queryset=Location.objects.all(),
        to_field_name="name",
        field_name="locations",
        label='Location (name or ID) (deprecated, use "locations" filter instead)',
    )
    locations = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        queryset=Location.objects.all(),
        to_field_name="name",
    )
    cloud_networks = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=CloudNetwork.objects.all(),
        to_field_name="name",
    )
    vpn_tunnel_endpoints = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VPNTunnelEndpoint.objects.all(),
        to_field_name="pk",
        label="VPN Tunnel Endpoint ID",
    )
    vpn_tunnel_endpoints_name_contains = django_filters.CharFilter(
        method="filter_vpntunnelendpoint_name_contains",
        label="VPN Tunnel Endpoint Name Contains",
    )

    class Meta:
        model = Prefix
        fields = ["date_allocated", "id", "prefix_length", "tags"]

    def _strip_values(self, values):
        result = []
        for value in values:
            value = value.strip()
            if is_uuid(value):
                result.append(Prefix.objects.get(pk=value).prefix)
            elif value:
                result.append(value)
        return result

    def filter_prefix(self, queryset, name, value):
        prefixes = self._strip_values(value)
        with contextlib.suppress(netaddr.AddrFormatError, ValueError):
            return queryset.net_equals(*prefixes)
        return queryset.none()

    def search_within(self, queryset, name, value):
        prefixes = self._strip_values(value)
        with contextlib.suppress(netaddr.AddrFormatError, ValueError):
            return queryset.net_contained(*prefixes)
        return queryset.none()

    def search_within_include(self, queryset, name, value):
        prefixes = self._strip_values(value)
        with contextlib.suppress(netaddr.AddrFormatError, ValueError):
            return queryset.net_contained_or_equal(*prefixes)
        return queryset.none()

    def search_contains(self, queryset, name, value):
        prefixes_queryset = queryset.none()
        values = self._strip_values(value)

        if prefixes := [prefix for prefix in values if "/" in prefix]:
            with contextlib.suppress(netaddr.AddrFormatError, ValueError):
                prefixes_queryset |= queryset.net_contains_or_equals(*prefixes)

        if prefixes_without_length := [prefix for prefix in values if "/" not in prefix]:
            query = Q()
            for _prefix in prefixes_without_length:
                with contextlib.suppress(netaddr.AddrFormatError, ValueError):
                    prefix = netaddr.IPAddress(_prefix)
                    query |= Q(network__lte=bytes(prefix), broadcast__gte=bytes(prefix))
            prefixes_queryset |= queryset.filter(query)
        return prefixes_queryset

    def filter_ancestors(self, queryset, name, value):
        if not value:
            return queryset
        prefixes = Prefix.objects.filter(pk__in=[v.id for v in value])
        ancestor_ids = [ancestor.id for prefix in prefixes for ancestor in prefix.ancestors()]
        return queryset.filter(pk__in=ancestor_ids)

    def generate_query_filter_present_in_vrf(self, value):
        if isinstance(value, (str, uuid.UUID)):
            value = VRF.objects.get(pk=value)

        query = Q(vrfs=value) | Q(vrfs__export_targets__in=value.import_targets.all())
        return query

    def filter_present_in_vrf(self, queryset, name, value):
        if value is None:
            return queryset.none
        params = self.generate_query_filter_present_in_vrf(value)
        return queryset.filter(params).distinct()

    def filter_vpntunnelendpoint_name_contains(self, queryset, name, value):
        return queryset.filter(vpn_tunnel_endpoints__name__contains=value)


class PrefixLocationAssignmentFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "location__name": "icontains",
        },
    )
    prefix = PrefixFilter()
    location = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Locations (name or ID)",
    )

    def _strip_values(self, values):
        return [value.strip() for value in values if value.strip()]

    class Meta:
        model = PrefixLocationAssignment
        fields = ["id", "prefix", "location"]


class IPAddressFilterSet(
    NautobotFilterSet,
    IPAMFilterSetMixin,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
):
    parent = ModelMultipleChoiceFilter(
        queryset=Prefix.objects.all(),
        label="Parent prefix",
    )
    prefix = MultiValueCharFilter(
        method="search_by_prefix",
        label="Contained in prefix",
    )
    address = MultiValueCharFilter(
        method="filter_address",
        label="Address",
    )
    vrfs = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="parent__vrfs",
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="VRF (ID or RD)",
    )
    # TODO: change to a multiple-value filter as a breaking change for dynamic groups and permissions definition
    present_in_vrf_id = django_filters.ModelChoiceFilter(
        field_name="parent__vrfs",
        queryset=VRF.objects.all(),
        method="filter_present_in_vrf",
        label="VRF (ID)",
    )
    # TODO: change to a multiple-value filter as a breaking change for dynamic groups and permissions definition
    present_in_vrf = django_filters.ModelChoiceFilter(
        field_name="parent__vrfs__rd",
        queryset=VRF.objects.all(),
        method="filter_present_in_vrf",
        to_field_name="rd",
        label="VRF (RD)",
    )
    device = MultiValueCharFilter(
        method="filter_device",
        field_name="name",
        label="Device (name)",
    )
    device_id = MultiValueUUIDFilter(
        method="filter_device",
        field_name="pk",
        label="Device (ID)",
    )
    virtual_machine = MultiValueCharFilter(
        method="filter_virtual_machine",
        field_name="name",
        label="Virtual machine (name)",
    )
    virtual_machine_id = MultiValueUUIDFilter(
        method="filter_virtual_machine",
        field_name="pk",
        label="Virtual machine (ID)",
    )
    interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Interface.objects.all(),
        to_field_name="name",
    )
    vm_interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VMInterface.objects.all(),
        to_field_name="name",
    )
    namespace = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Namespace.objects.all(),
        field_name="parent__namespace",
        to_field_name="name",
    )
    has_interface_assignments = RelatedMembershipBooleanFilter(
        field_name="interfaces",
        method="_has_interface_assignments",
        label="Has Interface Assignments",
    )
    nat_inside = ModelMultipleChoiceFilter(
        queryset=IPAddress.objects.all(),
        label="NAT (Inside)",
    )
    has_nat_inside = RelatedMembershipBooleanFilter(
        field_name="nat_inside",
        label="Has NAT Inside",
    )
    ip_version = django_filters.NumberFilter()
    services = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Service.objects.all(),
        to_field_name="name",
        label="Services (name or ID)",
    )

    class Meta:
        model = IPAddress
        fields = ["id", "dns_name", "type", "tags", "mask_length", "nat_inside", "description"]

    def generate_query__has_interface_assignments(self, value):
        """Helper method used by DynamicGroups and by _assigned_to_interface method."""
        if value is not None:
            if value:
                return Q(interfaces__isnull=False) | Q(vm_interfaces__isnull=False)
            else:
                return Q(interfaces__isnull=True) & Q(vm_interfaces__isnull=True)
        return Q()

    def _has_interface_assignments(self, queryset, name, value):
        params = self.generate_query__has_interface_assignments(value)
        return queryset.filter(params)

    def search_by_prefix(self, queryset, name, value):
        prefixes = []
        for prefix in value:
            prefix = prefix.strip()
            if is_uuid(prefix):
                prefixes.append(Prefix.objects.get(pk=prefix).prefix)
            elif prefix:
                prefixes.append(prefix)

        return queryset.net_host_contained(*prefixes)

    def filter_address(self, queryset, name, value):
        try:
            return queryset.net_in(value)
        except ValidationError:
            return queryset.none()

    def generate_query_filter_present_in_vrf(self, value):
        if isinstance(value, (str, uuid.UUID)):
            value = VRF.objects.get(pk=value)

        query = Q(parent__vrfs=value) | Q(parent__vrfs__export_targets__in=value.import_targets.all())
        return query

    def filter_present_in_vrf(self, queryset, name, value):
        if value is None:
            return queryset.none
        params = self.generate_query_filter_present_in_vrf(value)
        return queryset.filter(params).distinct()

    def filter_device(self, queryset, name, value):
        devices = Device.objects.filter(**{f"{name}__in": value})
        if not devices.exists():
            return queryset.none()
        interface_ids = []
        for device in devices:
            interface_ids.extend(device.vc_interfaces.values_list("id", flat=True))
        return queryset.filter(interfaces__in=interface_ids)

    def filter_virtual_machine(self, queryset, name, value):
        virtual_machines = VirtualMachine.objects.filter(**{f"{name}__in": value})
        if not virtual_machines.exists():
            return queryset.none()
        interface_ids = []
        for vm in virtual_machines:
            interface_ids.extend(vm.interfaces.values_list("id", flat=True))
        return queryset.filter(vm_interfaces__in=interface_ids)


class IPAddressToInterfaceFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "interface__name": "icontains",
            "vm_interface__name": "icontains",
        },
    )
    interface = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Interface.objects.all(),
    )
    vm_interface = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VMInterface.objects.all(),
    )

    class Meta:
        model = IPAddressToInterface
        fields = "__all__"


class VLANGroupFilterSet(NautobotFilterSet, LocatableModelFilterSetMixin, NameSearchFilterSet):
    class Meta:
        model = VLANGroup
        fields = ["id", "name", "description", "tags"]


class VLANFilterSet(
    NautobotFilterSet,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "vid": {
                "lookup_expr": "exact",
                "preprocessor": int,  # vid expects an int
            },
        },
    )
    available_on_device = MultiValueUUIDFilter(
        method="get_for_device",
        label="Device (ID)",
        field_name="pk",
    )
    vlan_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VLANGroup.objects.all(),
    )
    location = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        queryset=Location.objects.all(),
        to_field_name="name",
        field_name="locations",
        label='Location (name or ID) (deprecated, use "locations" filter instead)',
    )
    locations = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        queryset=Location.objects.all(),
        to_field_name="name",
    )

    class Meta:
        model = VLAN
        fields = ["id", "name", "tags", "vid"]

    def get_for_device(self, queryset, name, value):
        """Return all VLANs available to the specified Device(value)."""
        devices = Device.objects.select_related("location").filter(**{f"{name}__in": value})
        if not devices.exists():
            return queryset.none()
        location_ids = list(devices.values_list("location__id", flat=True))
        for location in Location.objects.filter(pk__in=location_ids):
            location_ids.extend([ancestor.id for ancestor in location.ancestors()])
        return queryset.filter(Q(locations__isnull=True) | Q(locations__in=location_ids))


class VLANLocationAssignmentFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "vlan__vid": "iexact",
            "location__name": "icontains",
        },
    )
    vlan = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="vid",
        queryset=VLAN.objects.all(),
        label="VLAN (VID or ID)",
    )
    location = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        queryset=Location.objects.all(),
        to_field_name="name",
    )

    class Meta:
        model = VLANLocationAssignment
        fields = ["id", "vlan", "location"]


class ServiceFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        },
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
    )
    virtual_machine = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualMachine.objects.all(),
        to_field_name="name",
    )
    ports = NumericArrayFilter(field_name="ports", lookup_expr="contains")

    class Meta:
        model = Service
        fields = ["id", "name", "protocol", "tags"]
