import django_filters
import netaddr
from django.core.exceptions import ValidationError
from django.db.models import Q
from netaddr.core import AddrFormatError

from nautobot.core.filters import (
    MultiValueCharFilter,
    MultiValueUUIDFilter,
    NameSlugSearchFilterSet,
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
    import_target_id = django_filters.ModelMultipleChoiceFilter(
        field_name="import_targets",
        queryset=RouteTarget.objects.all(),
        label="Import target (ID) - Deprecated (use import_target filter)",
    )
    import_target = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="import_targets",
        queryset=RouteTarget.objects.all(),
        to_field_name="name",
        label="Import target (ID or name)",
    )
    export_target_id = django_filters.ModelMultipleChoiceFilter(
        field_name="export_targets",
        queryset=RouteTarget.objects.all(),
        label="Export target (ID) - Deprecated (use export_target filter)",
    )
    export_target = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="export_targets",
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
        label="Device (ID or name)",
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
    importing_vrf_id = django_filters.ModelMultipleChoiceFilter(
        field_name="importing_vrfs",
        queryset=VRF.objects.all(),
        label="Importing VRF (ID) - Deprecated (use import_vrf filter)",
    )
    importing_vrf = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="importing_vrfs",
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="Import VRF (ID or RD)",
    )
    exporting_vrf_id = django_filters.ModelMultipleChoiceFilter(
        field_name="exporting_vrfs",
        queryset=VRF.objects.all(),
        label="Exporting VRF (ID) - Deprecated (use export_vrf filter)",
    )
    exporting_vrf = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="exporting_vrfs",
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="Export VRF (ID or RD)",
    )

    class Meta:
        model = RouteTarget
        fields = ["id", "name", "tags"]


class RIRFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
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
    # TODO(jathan): Since Prefixes are now assigned to VRFs via m2m and not the other way around via
    # FK, Filtering on the VRF by ID or RD needs to be inverted to filter on the m2m.
    """
    vrf_id = django_filters.ModelMultipleChoiceFilter(
        queryset=VRF.objects.all(),
        label="VRF (ID) - Deprecated (use vrf filter)",
    )
    vrf = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="VRF (ID or RD)",
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
    """
    vlan_id = django_filters.ModelMultipleChoiceFilter(
        queryset=VLAN.objects.all(),
        label="VLAN (ID)",
    )
    vlan_vid = django_filters.NumberFilter(
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

    class Meta:
        model = Prefix
        fields = ["date_allocated", "id", "ip_version", "prefix", "tags", "type"]

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


class IPAddressFilterSet(
    NautobotFilterSet,
    IPAMFilterSetMixin,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
):
    parent = django_filters.CharFilter(
        method="search_by_parent",
        label="Parent prefix",
    )
    address = MultiValueCharFilter(
        method="filter_address",
        label="Address",
    )
    vrf = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="parent__vrfs",
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="VRF (ID or RD)",
    )
    # TODO(jathan): Since Prefixes are now assigned to VRFs via m2m and not the other way around via
    # FK, Filtering on the VRF by ID or RD needs to be inherited from the parent prefix, after
    # Prefix -> IPAddress parenting has been implemented.
    """
    present_in_vrf_id = django_filters.ModelChoiceFilter(
        field_name="vrf",
        queryset=VRF.objects.all(),
        method="filter_present_in_vrf",
        label="VRF (ID)",
    )
    present_in_vrf = django_filters.ModelChoiceFilter(
        field_name="vrf__rd",
        queryset=VRF.objects.all(),
        method="filter_present_in_vrf",
        to_field_name="rd",
        label="VRF (RD)",
    )
    """
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

    class Meta:
        model = IPAddress
        fields = ["id", "ip_version", "dns_name", "type", "tags", "mask_length"]

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
        return queryset.filter(interfaces__in=interface_ids)

    def filter_virtual_machine(self, queryset, name, value):
        virtual_machines = VirtualMachine.objects.filter(**{f"{name}__in": value})
        if not virtual_machines.exists():
            return queryset.none()
        interface_ids = []
        for vm in virtual_machines:
            interface_ids.extend(vm.interfaces.values_list("id", flat=True))
        return queryset.filter(vm_interfaces__in=interface_ids)


class VLANGroupFilterSet(NautobotFilterSet, LocatableModelFilterSetMixin, NameSlugSearchFilterSet):
    class Meta:
        model = VLANGroup
        fields = ["id", "name", "slug", "description"]


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
        label="VLAN Group (slug or ID)",
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
    device_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label="Device (ID) - Deprecated (use device filter)",
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (ID or name)",
    )
    virtual_machine_id = django_filters.ModelMultipleChoiceFilter(
        queryset=VirtualMachine.objects.all(),
        label="Virtual machine (ID) - Deprecated (use virtual_machine filter)",
    )
    virtual_machine = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualMachine.objects.all(),
        to_field_name="name",
        label="Virtual machine (ID or name)",
    )
    port = NumericArrayFilter(field_name="ports", lookup_expr="contains")

    class Meta:
        model = Service
        fields = ["id", "name", "protocol", "tags"]
