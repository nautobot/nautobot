from django.db.models import Q
import django_filters

from nautobot.core.filters import (
    BaseFilterSet,
    ModelMultipleChoiceFilter,
    MultiValueCharFilter,
    MultiValueMACAddressFilter,
    NameSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    TreeNodeMultipleChoiceFilter,
)
from nautobot.core.utils.data import is_uuid
from nautobot.dcim.filters import LocatableModelFilterSetMixin
from nautobot.dcim.models import Device, Location, Platform, SoftwareImageFile, SoftwareVersion
from nautobot.extras.filters import (
    CustomFieldModelFilterSetMixin,
    LocalContextModelFilterSetMixin,
    NautobotFilterSet,
    RoleModelFilterSetMixin,
    StatusModelFilterSetMixin,
)
from nautobot.ipam.models import IPAddress, Service, VLAN, VRF
from nautobot.tenancy.filters import TenancyModelFilterSetMixin

from .models import Cluster, ClusterGroup, ClusterType, VirtualMachine, VMInterface

__all__ = (
    "ClusterFilterSet",
    "ClusterGroupFilterSet",
    "ClusterTypeFilterSet",
    "VMInterfaceFilterSet",
    "VirtualMachineFilterSet",
)


class ClusterTypeFilterSet(NautobotFilterSet, NameSearchFilterSet):
    clusters = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Cluster.objects.all(),
        to_field_name="name",
    )
    has_clusters = RelatedMembershipBooleanFilter(
        field_name="clusters",
        label="Has clusters",
    )

    class Meta:
        model = ClusterType
        fields = ["id", "name", "description"]


class ClusterGroupFilterSet(NautobotFilterSet, NameSearchFilterSet):
    clusters = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Cluster.objects.all(),
        to_field_name="name",
    )
    has_clusters = RelatedMembershipBooleanFilter(
        field_name="clusters",
        label="Has clusters",
    )

    class Meta:
        model = ClusterGroup
        fields = ["id", "name", "description"]


class ClusterFilterSet(NautobotFilterSet, LocatableModelFilterSetMixin, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "comments": "icontains",
        },
    )
    devices = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Device.objects.all(),
    )
    has_devices = RelatedMembershipBooleanFilter(
        field_name="devices",
        label="Has devices",
    )
    virtual_machines = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=VirtualMachine.objects.all(),
    )
    has_virtual_machines = RelatedMembershipBooleanFilter(
        field_name="virtual_machines",
        label="Has virtual machines",
    )
    cluster_group_id = ModelMultipleChoiceFilter(
        field_name="cluster_group",
        queryset=ClusterGroup.objects.all(),
        label="Parent cluster group (ID) - Deprecated (use cluster_group filter)",
    )
    cluster_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ClusterGroup.objects.all(),
        label="Parent cluster group (ID or name)",
        to_field_name="name",
    )
    cluster_type_id = ModelMultipleChoiceFilter(
        field_name="cluster_type",
        queryset=ClusterType.objects.all(),
        label="Cluster type (ID) - Deprecated (use cluster_type filter)",
    )
    cluster_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ClusterType.objects.all(),
        to_field_name="name",
    )

    class Meta:
        model = Cluster
        fields = ["id", "comments", "name", "tags"]


class VirtualMachineFilterSet(
    NautobotFilterSet,
    LocalContextModelFilterSetMixin,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
    RoleModelFilterSetMixin,
):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "comments": "icontains",
        },
    )
    cluster_group_id = ModelMultipleChoiceFilter(
        field_name="cluster__cluster_group",
        queryset=ClusterGroup.objects.all(),
        label="Cluster group (ID) - Deprecated (use cluster_group filter)",
    )
    cluster_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="cluster__cluster_group",
        queryset=ClusterGroup.objects.all(),
        to_field_name="name",
    )
    cluster_type_id = ModelMultipleChoiceFilter(
        field_name="cluster__cluster_type",
        queryset=ClusterType.objects.all(),
        label="Cluster type (ID) - Deprecated (use cluster_type filter)",
    )
    cluster_type = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="cluster__cluster_type",
        queryset=ClusterType.objects.all(),
        to_field_name="name",
    )
    cluster_id = ModelMultipleChoiceFilter(
        queryset=Cluster.objects.all(),
        label="Cluster (ID) - Deprecated (use cluster filter)",
    )
    cluster = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Cluster.objects.all(),
        to_field_name="name",
    )
    location = TreeNodeMultipleChoiceFilter(
        prefers_id=True,
        queryset=Location.objects.all(),
        field_name="cluster__location",
        to_field_name="name",
        label="Location (name or ID)",
    )
    platform_id = ModelMultipleChoiceFilter(
        queryset=Platform.objects.all(),
        label="Platform (ID) - Deprecated (use platform filter)",
    )
    platform = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Platform.objects.all(),
        to_field_name="name",
    )
    mac_address = MultiValueMACAddressFilter(
        field_name="interfaces__mac_address",
        label="MAC address",
    )
    has_primary_ip = django_filters.BooleanFilter(
        method="_has_primary_ip",
        label="Has a primary IP",
    )
    primary_ip4 = MultiValueCharFilter(
        method="filter_primary_ip4",
        label="Primary IPv4 Address (address or ID)",
    )
    primary_ip6 = MultiValueCharFilter(
        method="filter_primary_ip6",
        label="Primary IPv6 Address (address or ID)",
    )
    services = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Service.objects.all(),
    )
    has_services = RelatedMembershipBooleanFilter(
        field_name="services",
        label="Has services",
    )
    interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VMInterface.objects.all(),
        to_field_name="name",
    )
    has_interfaces = RelatedMembershipBooleanFilter(
        field_name="interfaces",
        label="Has interfaces",
    )
    has_software_image_files = RelatedMembershipBooleanFilter(
        field_name="software_image_files",
        label="Has software image files",
    )
    software_image_files = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SoftwareImageFile.objects.all(),
        to_field_name="image_file_name",
    )
    has_software_version = RelatedMembershipBooleanFilter(
        field_name="software_version",
        label="Has software version",
    )
    software_version = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=SoftwareVersion.objects.all(),
        to_field_name="version",
    )
    ip_addresses = MultiValueCharFilter(
        method="filter_ip_addresses",
        label="IP addresses (address or ID)",
        distinct=True,
    )
    has_ip_addresses = RelatedMembershipBooleanFilter(field_name="interfaces__ip_addresses", label="Has IP addresses")
    vrfs = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VRF.objects.all(),
        to_field_name="rd",
        label="VRFs (ID or RD)",
    )

    def filter_ip_addresses(self, queryset, name, value):
        pk_values = set(item for item in value if is_uuid(item))
        addresses = set(item for item in value if item not in pk_values)

        ip_queryset = IPAddress.objects.filter_address_or_pk_in(addresses, pk_values)
        return queryset.filter(interfaces__ip_addresses__in=ip_queryset).distinct()

    class Meta:
        model = VirtualMachine
        fields = [
            "id",
            "name",
            "vcpus",
            "memory",
            "disk",
            "comments",
            "has_software_image_files",
            "software_image_files",
            "has_software_version",
            "software_version",
            "tags",
        ]

    def generate_query__has_primary_ip(self, value):
        query = Q(primary_ip4__isnull=False) | Q(primary_ip6__isnull=False)
        if not value:
            return ~query
        return query

    def _has_primary_ip(self, queryset, name, value):
        params = self.generate_query__has_primary_ip(value)
        return queryset.filter(params)

    # 2.0 TODO(jathan): Eliminate these methods.
    def filter_primary_ip4(self, queryset, name, value):
        pk_values = set(item for item in value if is_uuid(item))
        addresses = set(item for item in value if item not in pk_values)

        ip_queryset = IPAddress.objects.filter_address_or_pk_in(addresses, pk_values)
        return queryset.filter(primary_ip4__in=ip_queryset)

    def filter_primary_ip6(self, queryset, name, value):
        pk_values = set(item for item in value if is_uuid(item))
        addresses = set(item for item in value if item not in pk_values)

        ip_queryset = IPAddress.objects.filter_address_or_pk_in(addresses, pk_values)
        return queryset.filter(primary_ip6__in=ip_queryset)


class VMInterfaceFilterSet(
    BaseFilterSet, RoleModelFilterSetMixin, StatusModelFilterSetMixin, CustomFieldModelFilterSetMixin
):
    q = SearchFilter(filter_predicates={"name": "icontains"})

    cluster_id = ModelMultipleChoiceFilter(
        field_name="virtual_machine__cluster",
        queryset=Cluster.objects.all(),
        label="Cluster (ID) - Deprecated (use cluster filter)",
    )
    cluster = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="virtual_machine__cluster",
        queryset=Cluster.objects.all(),
        to_field_name="name",
    )
    virtual_machine_id = ModelMultipleChoiceFilter(
        field_name="virtual_machine",
        queryset=VirtualMachine.objects.all(),
        label="Virtual machine (ID) - Deprecated (use virtual_machine filter)",
    )
    virtual_machine = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualMachine.objects.all(),
        to_field_name="name",
    )
    parent_interface = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=VMInterface.objects.all(),
    )
    child_interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=VMInterface.objects.all(),
    )
    has_child_interfaces = RelatedMembershipBooleanFilter(
        field_name="child_interfaces",
        label="Has child interfaces",
    )
    bridge = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=VMInterface.objects.all(),
    )
    bridged_interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=VMInterface.objects.all(),
    )
    has_bridged_interfaces = RelatedMembershipBooleanFilter(
        field_name="bridged_interfaces",
        label="Has Bridged Interfaces",
    )
    mac_address = MultiValueMACAddressFilter(
        label="MAC address",
    )
    tagged_vlans = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="vid",
        queryset=VLAN.objects.all(),
    )
    has_tagged_vlans = RelatedMembershipBooleanFilter(
        field_name="tagged_vlans",
        label="Has Tagged VLANs",
    )
    untagged_vlan = NaturalKeyOrPKMultipleChoiceFilter(
        prefers_id=True,
        to_field_name="vid",
        queryset=VLAN.objects.all(),
    )
    vlan_id = django_filters.CharFilter(method="filter_vlan_id", label="Any assigned VLAN (tagged or untagged)")
    ip_addresses = MultiValueCharFilter(
        method="filter_ip_addresses",
        label="IP addresses (address or ID)",
        distinct=True,
    )
    has_ip_addresses = RelatedMembershipBooleanFilter(field_name="ip_addresses", label="Has IP addresses")

    def filter_ip_addresses(self, queryset, name, value):
        pk_values = set(item for item in value if is_uuid(item))
        addresses = set(item for item in value if item not in pk_values)

        ip_queryset = IPAddress.objects.filter_address_or_pk_in(addresses, pk_values)
        return queryset.filter(ip_addresses__in=ip_queryset).distinct()

    def filter_vlan_id(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(Q(untagged_vlan_id=value) | Q(tagged_vlans=value))

    class Meta:
        model = VMInterface
        fields = ["id", "name", "description", "enabled", "mtu", "mode", "tags"]
