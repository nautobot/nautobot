import django_filters
import netaddr
from django.core.exceptions import ValidationError
from django.db.models import Q
from netaddr.core import AddrFormatError

from nautobot.dcim.filters import LocatableModelFilterSetMixin
from nautobot.dcim.models import Device, Interface
from nautobot.extras.filters import NautobotFilterSet, StatusModelFilterSetMixin
from nautobot.tenancy.filters import TenancyModelFilterSetMixin
from nautobot.utilities.filters import (
    MultiValueCharFilter,
    MultiValueUUIDFilter,
    NameSlugSearchFilterSet,
    NumericArrayFilter,
    SearchFilter,
    TagFilter,
)
from nautobot.virtualization.models import VirtualMachine, VMInterface
from .choices import IPAddressRoleChoices
from .models import (
    Aggregate,
    IPAddress,
    Prefix,
    RIR,
    Role,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)


__all__ = (
    "AggregateFilterSet",
    "IPAddressFilterSet",
    "PrefixFilterSet",
    "RIRFilterSet",
    "RoleFilterSet",
    "RouteTargetFilterSet",
    "ServiceFilterSet",
    "VLANFilterSet",
    "VLANGroupFilterSet",
    "VRFFilterSet",
)


class VRFFilterSet(NautobotFilterSet, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "rd": "icontains",
            "description": "icontains",
        },
    )
    import_target_id = django_filters.ModelMultipleChoiceFilter(
        field_name="import_targets",
        queryset=RouteTarget.objects.all(),
        label="Import target",
    )
    import_target = django_filters.ModelMultipleChoiceFilter(
        field_name="import_targets__name",
        queryset=RouteTarget.objects.all(),
        to_field_name="name",
        label="Import target (name)",
    )
    export_target_id = django_filters.ModelMultipleChoiceFilter(
        field_name="export_targets",
        queryset=RouteTarget.objects.all(),
        label="Export target",
    )
    export_target = django_filters.ModelMultipleChoiceFilter(
        field_name="export_targets__name",
        queryset=RouteTarget.objects.all(),
        to_field_name="name",
        label="Export target (name)",
    )
    tag = TagFilter()

    class Meta:
        model = VRF
        fields = ["id", "name", "rd", "enforce_unique"]


class RouteTargetFilterSet(NautobotFilterSet, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        },
    )
    importing_vrf_id = django_filters.ModelMultipleChoiceFilter(
        field_name="importing_vrfs",
        queryset=VRF.objects.all(),
        label="Importing VRF",
    )
    importing_vrf = django_filters.ModelMultipleChoiceFilter(
        field_name="importing_vrfs__rd",
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="Import VRF (RD)",
    )
    exporting_vrf_id = django_filters.ModelMultipleChoiceFilter(
        field_name="exporting_vrfs",
        queryset=VRF.objects.all(),
        label="Exporting VRF",
    )
    exporting_vrf = django_filters.ModelMultipleChoiceFilter(
        field_name="exporting_vrfs__rd",
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="Export VRF (RD)",
    )
    tag = TagFilter()

    class Meta:
        model = RouteTarget
        fields = ["id", "name"]


class RIRFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    class Meta:
        model = RIR
        fields = ["id", "name", "slug", "is_private", "description"]


class IPAMFilterSetMixin(django_filters.FilterSet):
    """Filterset mixin to add shared filters across all IPAM objects."""

    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )
    family = django_filters.NumberFilter(
        method="filter_ip_family",
        label="Family",
    )

    def search(self, qs, name, value):
        value = value.strip()

        if not value:
            return qs

        return qs.string_search(value)

    def filter_ip_family(self, qs, name, value):
        return qs.ip_family(value)


class AggregateFilterSet(NautobotFilterSet, IPAMFilterSetMixin, TenancyModelFilterSetMixin):
    prefix = django_filters.CharFilter(
        method="filter_prefix",
        label="Prefix",
    )
    rir_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RIR.objects.all(),
        label="RIR (ID)",
    )
    rir = django_filters.ModelMultipleChoiceFilter(
        field_name="rir__slug",
        queryset=RIR.objects.all(),
        to_field_name="slug",
        label="RIR (slug)",
    )
    tag = TagFilter()

    class Meta:
        model = Aggregate
        fields = ["id", "date_added"]

    def filter_prefix(self, queryset, name, value):
        if not value.strip():
            return queryset
        try:
            return queryset.net_equals(netaddr.IPNetwork(value))
        except (AddrFormatError, ValueError):
            return queryset.none()


class RoleFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    class Meta:
        model = Role
        fields = ["id", "name", "slug"]


class PrefixFilterSet(
    NautobotFilterSet,
    IPAMFilterSetMixin,
    LocatableModelFilterSetMixin,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
):
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
    mask_length = django_filters.NumberFilter(label="mask_length", method="filter_prefix_length_eq")
    mask_length__gte = django_filters.NumberFilter(label="mask_length__gte", method="filter_prefix_length_gte")
    mask_length__lte = django_filters.NumberFilter(label="mask_length__lte", method="filter_prefix_length_lte")
    vrf_id = django_filters.ModelMultipleChoiceFilter(
        queryset=VRF.objects.all(),
        label="VRF",
    )
    vrf = django_filters.ModelMultipleChoiceFilter(
        field_name="vrf__rd",
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="VRF (RD)",
    )
    present_in_vrf_id = django_filters.ModelChoiceFilter(
        field_name="vrf",
        queryset=VRF.objects.all(),
        method="filter_present_in_vrf",
        label="VRF",
    )
    present_in_vrf = django_filters.ModelChoiceFilter(
        field_name="vrf__rd",
        queryset=VRF.objects.all(),
        method="filter_present_in_vrf",
        to_field_name="rd",
        label="VRF (RD)",
    )
    vlan_id = django_filters.ModelMultipleChoiceFilter(
        queryset=VLAN.objects.all(),
        label="VLAN (ID)",
    )
    vlan_vid = django_filters.NumberFilter(
        field_name="vlan__vid",
        label="VLAN number (1-4095)",
    )
    role_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Role.objects.all(),
        label="Role (ID)",
    )
    role = django_filters.ModelMultipleChoiceFilter(
        field_name="role__slug",
        queryset=Role.objects.all(),
        to_field_name="slug",
        label="Role (slug)",
    )
    tag = TagFilter()

    class Meta:
        model = Prefix
        fields = ["id", "is_pool", "prefix"]

    def filter_prefix(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        # filter for Prefix models equal to |value|
        try:
            return queryset.net_equals(netaddr.IPNetwork(value))
        except (AddrFormatError, ValueError):
            return queryset.none()

    def filter_prefix_length_eq(self, queryset, name, value):
        return queryset.filter(prefix_length__exact=value)

    def filter_prefix_length_lte(self, queryset, name, value):
        return queryset.filter(prefix_length__lte=value)

    def filter_prefix_length_gte(self, queryset, name, value):
        return queryset.filter(prefix_length__gte=value)

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

        # This stringification is done to make the `pretty_print_query()` output look human-readable,
        # and nothing more. It would work as complex objects but looks bad in the web UI.
        targets = [str(t) for t in value.import_targets.values_list("pk", flat=True)]
        query = Q(vrf=str(value.pk)) | Q(vrf__export_targets__in=targets)
        return query

    def filter_present_in_vrf(self, queryset, name, value):
        params = self.generate_query_filter_present_in_vrf(value)
        return queryset.filter(params)


class IPAddressFilterSet(NautobotFilterSet, IPAMFilterSetMixin, TenancyModelFilterSetMixin, StatusModelFilterSetMixin):
    parent = django_filters.CharFilter(
        method="search_by_parent",
        label="Parent prefix",
    )
    address = MultiValueCharFilter(
        method="filter_address",
        label="Address",
    )
    mask_length = django_filters.NumberFilter(
        method="filter_mask_length",
        label="Mask length",
    )
    vrf_id = django_filters.ModelMultipleChoiceFilter(
        queryset=VRF.objects.all(),
        label="VRF",
    )
    vrf = django_filters.ModelMultipleChoiceFilter(
        field_name="vrf__rd",
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="VRF (RD)",
    )
    present_in_vrf_id = django_filters.ModelChoiceFilter(
        field_name="vrf",
        queryset=VRF.objects.all(),
        method="filter_present_in_vrf",
        label="VRF",
    )
    present_in_vrf = django_filters.ModelChoiceFilter(
        field_name="vrf__rd",
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
    interface = django_filters.ModelMultipleChoiceFilter(
        field_name="interface__name",
        queryset=Interface.objects.all(),
        to_field_name="name",
        label="Interface (name)",
    )
    interface_id = django_filters.ModelMultipleChoiceFilter(
        field_name="interface",
        queryset=Interface.objects.all(),
        label="Interface (ID)",
    )
    vminterface = django_filters.ModelMultipleChoiceFilter(
        field_name="vminterface__name",
        queryset=VMInterface.objects.all(),
        to_field_name="name",
        label="VM interface (name)",
    )
    vminterface_id = django_filters.ModelMultipleChoiceFilter(
        field_name="vminterface",
        queryset=VMInterface.objects.all(),
        label="VM interface (ID)",
    )
    assigned_to_interface = django_filters.BooleanFilter(
        method="_assigned_to_interface",
        label="Is assigned to an interface",
    )
    role = django_filters.MultipleChoiceFilter(choices=IPAddressRoleChoices)
    tag = TagFilter()

    class Meta:
        model = IPAddress
        fields = ["id", "dns_name"]

    def search_by_parent(self, queryset, name, value):
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

    def filter_mask_length(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(prefix_length=value)

    def filter_present_in_vrf(self, queryset, name, value):
        if value is None:
            return queryset.none
        return queryset.filter(Q(vrf=value) | Q(vrf__export_targets__in=value.import_targets.all()))

    def filter_device(self, queryset, name, value):
        devices = Device.objects.filter(**{f"{name}__in": value})
        if not devices.exists():
            return queryset.none()
        interface_ids = []
        for device in devices:
            interface_ids.extend(device.vc_interfaces.values_list("id", flat=True))
        return queryset.filter(interface__in=interface_ids)

    def filter_virtual_machine(self, queryset, name, value):
        virtual_machines = VirtualMachine.objects.filter(**{f"{name}__in": value})
        if not virtual_machines.exists():
            return queryset.none()
        interface_ids = []
        for vm in virtual_machines:
            interface_ids.extend(vm.interfaces.values_list("id", flat=True))
        return queryset.filter(vminterface__in=interface_ids)

    def _assigned_to_interface(self, queryset, name, value):
        return queryset.exclude(assigned_object_id__isnull=value)


class VLANGroupFilterSet(NautobotFilterSet, LocatableModelFilterSetMixin, NameSlugSearchFilterSet):
    class Meta:
        model = VLANGroup
        fields = ["id", "name", "slug", "description"]


class VLANFilterSet(
    NautobotFilterSet,
    LocatableModelFilterSetMixin,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
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
    available_on_device = django_filters.UUIDFilter(
        method="get_for_device",
        label="Device (ID)",
        field_name="pk",
    )
    group_id = django_filters.ModelMultipleChoiceFilter(
        queryset=VLANGroup.objects.all(),
        label="Group (ID)",
    )
    group = django_filters.ModelMultipleChoiceFilter(
        field_name="group__slug",
        queryset=VLANGroup.objects.all(),
        to_field_name="slug",
        label="Group",
    )
    role_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Role.objects.all(),
        label="Role (ID)",
    )
    role = django_filters.ModelMultipleChoiceFilter(
        field_name="role__slug",
        queryset=Role.objects.all(),
        to_field_name="slug",
        label="Role (slug)",
    )
    tag = TagFilter()

    class Meta:
        model = VLAN
        fields = ["id", "vid", "name"]

    def get_for_device(self, queryset, name, value):
        """Return all VLANs available to the specified Device(value)."""
        try:
            device = Device.objects.get(id=value)
            return queryset.filter(Q(site__isnull=True) | Q(site=device.site))
        except Device.DoesNotExist:
            return queryset.none()


class ServiceFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        },
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label="Device (ID)",
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name="device__name",
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name)",
    )
    virtual_machine_id = django_filters.ModelMultipleChoiceFilter(
        queryset=VirtualMachine.objects.all(),
        label="Virtual machine (ID)",
    )
    virtual_machine = django_filters.ModelMultipleChoiceFilter(
        field_name="virtual_machine__name",
        queryset=VirtualMachine.objects.all(),
        to_field_name="name",
        label="Virtual machine (name)",
    )
    port = NumericArrayFilter(field_name="ports", lookup_expr="contains")
    tag = TagFilter()

    class Meta:
        model = Service
        fields = ["id", "name", "protocol"]
