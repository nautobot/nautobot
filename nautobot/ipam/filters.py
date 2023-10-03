import django_filters
import netaddr
from django.core.exceptions import ValidationError
from django.db.models import Q
from netaddr.core import AddrFormatError

from nautobot.core.filters import (
    MultiValueCharFilter,
    MultiValueNumberFilter,
    MultiValueUUIDFilter,
    NameSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    NumericArrayFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
)
from nautobot.dcim.filters import LocatableModelFilterSetMixin
from nautobot.dcim.models import Device, Interface
from nautobot.extras.filters import NautobotFilterSet, RoleModelFilterSetMixin, StatusModelFilterSetMixin
from nautobot.ipam import choices
from nautobot.tenancy.filters import TenancyModelFilterSetMixin
from nautobot.virtualization.models import VirtualMachine, VMInterface
from .models import (
    IPAddress,
    IPAddressToInterface,
    Namespace,
    Prefix,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)


__all__ = (
    "IPAddressFilterSet",
    "NamespaceFilterSet",
    "PrefixFilterSet",
    "RIRFilterSet",
    "RouteTargetFilterSet",
    "ServiceFilterSet",
    "VLANFilterSet",
    "VLANGroupFilterSet",
    "VRFFilterSet",
)


class NamespaceFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
        },
    )

    class Meta:
        model = Namespace
        fields = "__all__"


class VRFFilterSet(NautobotFilterSet, TenancyModelFilterSetMixin):
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
        label="Import target (ID or name)",
    )
    export_targets = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=RouteTarget.objects.all(),
        to_field_name="name",
        label="Export target (ID or name)",
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="devices",
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (ID or name)",
    )
    prefix = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="prefixes",
        queryset=Prefix.objects.all(),
        to_field_name="pk",  # TODO(jathan): Make this work with `prefix` "somehow"
        label="Prefix (ID or name)",
    )
    namespace = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Namespace.objects.all(),
        to_field_name="name",
        label="Namespace (name or ID)",
    )

    class Meta:
        model = VRF
        fields = ["id", "name", "rd", "tags"]


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
    LocatableModelFilterSetMixin,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
):
    # Prefix doesn't have an appropriate single natural-key field for a NaturalKeyOrPKMultipleChoiceFilter
    parent = django_filters.ModelMultipleChoiceFilter(
        queryset=Prefix.objects.all(),
    )
    prefix = django_filters.CharFilter(
        method="filter_prefix",
        label="Prefix",
    )
    within = django_filters.CharFilter(
        method="search_within",
        label="Within prefix",
    )
    within_include = django_filters.CharFilter(
        method="search_within_include",
        label="Within and including prefix",
    )
    contains = django_filters.CharFilter(
        method="search_contains",
        label="Prefixes which contain this prefix or IP",
    )
    vrfs = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="Assigned VRF (ID or RD)",
    )
    present_in_vrf_id = django_filters.ModelChoiceFilter(
        field_name="vrfs",
        queryset=VRF.objects.all(),
        method="filter_present_in_vrf",
        label="Present in VRF",
    )
    present_in_vrf = django_filters.ModelChoiceFilter(
        field_name="vrfs__rd",
        queryset=VRF.objects.all(),
        method="filter_present_in_vrf",
        to_field_name="rd",
        label="Present in VRF (RD)",
    )
    vlan_id = django_filters.ModelMultipleChoiceFilter(
        queryset=VLAN.objects.all(),
        label="VLAN (ID)",
    )
    vlan_vid = MultiValueNumberFilter(
        field_name="vlan__vid",
        label="VLAN number (1-4095)",
    )
    rir = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=RIR.objects.all(),
        label="RIR (name or ID)",
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
        label="Namespace (name or ID)",
    )
    ip_version = django_filters.NumberFilter()

    class Meta:
        model = Prefix
        fields = ["date_allocated", "id", "prefix_length", "tags"]

    def filter_prefix(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        # filter for Prefix models equal to |value|
        try:
            return queryset.net_equals(netaddr.IPNetwork(value))
        except (AddrFormatError, ValueError):
            return queryset.none()

    def search_within(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        try:
            return queryset.net_contained(netaddr.IPNetwork(value))
        except (AddrFormatError, ValueError):
            return queryset.none()

    def search_within_include(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        try:
            return queryset.net_contained_or_equal(netaddr.IPNetwork(value))
        except (AddrFormatError, ValueError):
            return queryset.none()

    def search_contains(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        try:
            # Searching by prefix
            if "/" in value:
                return queryset.net_contains_or_equals(netaddr.IPNetwork(value).cidr)
            # Searching by IP address
            else:
                # filter for Prefixes containing |value|
                # netaddr.IPAddress objects have no netmask
                # so prefix_length is not considered
                query = netaddr.IPAddress(value)
                return queryset.filter(
                    network__lte=bytes(query),
                    broadcast__gte=bytes(query),
                )
        except (AddrFormatError, ValueError):
            return queryset.none()

    def generate_query_filter_present_in_vrf(self, value):
        if isinstance(value, str):
            value = VRF.objects.get(pk=value)

        query = Q(vrfs=value) | Q(vrfs__export_targets__in=value.import_targets.all())
        return query

    def filter_present_in_vrf(self, queryset, name, value):
        if value is None:
            return queryset.none
        params = self.generate_query_filter_present_in_vrf(value)
        return queryset.filter(params).distinct()


class IPAddressFilterSet(
    NautobotFilterSet,
    IPAMFilterSetMixin,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
):
    parent = django_filters.ModelMultipleChoiceFilter(
        queryset=Prefix.objects.all(),
        label="Parent prefix",
    )
    prefix = django_filters.CharFilter(
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
    present_in_vrf_id = django_filters.ModelChoiceFilter(
        field_name="parent__vrfs",
        queryset=VRF.objects.all(),
        method="filter_present_in_vrf",
        label="VRF (ID)",
    )
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
        label="Interfaces (ID or name)",
    )
    vm_interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VMInterface.objects.all(),
        to_field_name="name",
        label="VM interfaces (ID or name)",
    )
    namespace = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Namespace.objects.all(),
        field_name="parent__namespace",
        to_field_name="name",
        label="Namespace (name or ID)",
    )
    has_interface_assignments = RelatedMembershipBooleanFilter(
        field_name="interfaces",
        method="_has_interface_assignments",
        label="Has Interface Assignments",
    )
    ip_version = django_filters.NumberFilter()

    class Meta:
        model = IPAddress
        fields = ["id", "dns_name", "type", "tags", "mask_length"]

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
        value = value.strip()
        if not value:
            return queryset
        try:
            query = netaddr.IPNetwork(value.strip()).cidr
            return queryset.net_host_contained(query)
        except (AddrFormatError, ValueError):
            return queryset.none()

    def filter_address(self, queryset, name, value):
        try:
            return queryset.net_in(value)
        except ValidationError:
            return queryset.none()

    def generate_query_filter_present_in_vrf(self, value):
        if isinstance(value, str):
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
    interface = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Interface.objects.all(),
        label="Interface (name or ID)",
    )
    ip_address = django_filters.ModelMultipleChoiceFilter(
        queryset=IPAddress.objects.all(),
        label="IP Address (ID)",
    )
    vm_interface = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VMInterface.objects.all(),
        label="VM Interface (name or ID)",
    )

    class Meta:
        model = IPAddressToInterface
        fields = "__all__"


class VLANGroupFilterSet(NautobotFilterSet, LocatableModelFilterSetMixin, NameSearchFilterSet):
    class Meta:
        model = VLANGroup
        fields = ["id", "name", "description"]


class VLANFilterSet(
    NautobotFilterSet,
    LocatableModelFilterSetMixin,
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
        label="VLAN Group (name or ID)",
    )

    class Meta:
        model = VLAN
        fields = ["id", "name", "tags", "vid"]

    def get_for_device(self, queryset, name, value):
        # TODO: after Location model replaced Site, which was not a hierarchical model, should we consider to include
        # VLANs that belong to the parent/child locations of the `device.location`?
        """Return all VLANs available to the specified Device(value)."""
        devices = Device.objects.select_related("location").filter(**{f"{name}__in": value})
        if not devices.exists():
            return queryset.none()
        location_ids = list(devices.values_list("location__id", flat=True))
        return queryset.filter(Q(location__isnull=True) | Q(location__in=location_ids))


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
        label="Device (ID or name)",
    )
    virtual_machine = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualMachine.objects.all(),
        to_field_name="name",
        label="Virtual machine (ID or name)",
    )
    ports = NumericArrayFilter(field_name="ports", lookup_expr="contains")

    class Meta:
        model = Service
        fields = ["id", "name", "protocol", "tags"]
