import django_filters
from django.db.models import Q

from nautobot.dcim.filters import LocatableModelFilterSetMixin
from nautobot.dcim.models import Device, DeviceRole, Location, Platform, Region, Site
from nautobot.extras.filters import (
    CustomFieldModelFilterSetMixin,
    LocalContextModelFilterSetMixin,
    NautobotFilterSet,
    StatusModelFilterSetMixin,
)
from nautobot.ipam.models import IPAddress, Service, VLAN
from nautobot.tenancy.filters import TenancyModelFilterSetMixin
from nautobot.utilities.filters import (
    BaseFilterSet,
    MultiValueCharFilter,
    MultiValueMACAddressFilter,
    NameSlugSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    TagFilter,
    TreeNodeMultipleChoiceFilter,
)
from nautobot.utilities.utils import is_uuid

from .models import Cluster, ClusterGroup, ClusterType, VirtualMachine, VMInterface

__all__ = (
    "ClusterFilterSet",
    "ClusterGroupFilterSet",
    "ClusterTypeFilterSet",
    "VirtualMachineFilterSet",
    "VMInterfaceFilterSet",
)


class ClusterTypeFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    clusters = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Cluster.objects.all(),
        to_field_name="name",
        label="Clusters (name or ID)",
    )
    has_clusters = RelatedMembershipBooleanFilter(
        field_name="clusters",
        label="Has clusters",
    )

    class Meta:
        model = ClusterType
        fields = ["id", "name", "slug", "description"]


class ClusterGroupFilterSet(NautobotFilterSet, NameSlugSearchFilterSet):
    clusters = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Cluster.objects.all(),
        to_field_name="name",
        label="Clusters (name or ID)",
    )
    has_clusters = RelatedMembershipBooleanFilter(
        field_name="clusters",
        label="Has clusters",
    )

    class Meta:
        model = ClusterGroup
        fields = ["id", "name", "slug", "description"]


class ClusterFilterSet(NautobotFilterSet, LocatableModelFilterSetMixin, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "comments": "icontains",
        },
    )
    devices = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name", queryset=Device.objects.all(), label="Devices (name or ID)"
    )
    has_devices = RelatedMembershipBooleanFilter(
        field_name="devices",
        label="Has devices",
    )
    virtual_machines = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=VirtualMachine.objects.all(),
        label="Virtual machines (name or ID)",
    )
    has_virtual_machines = RelatedMembershipBooleanFilter(
        field_name="virtual_machines",
        label="Has virtual machines",
    )
    group_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ClusterGroup.objects.all(),
        label="Parent group (ID)",
    )
    group = django_filters.ModelMultipleChoiceFilter(
        field_name="group__slug",
        queryset=ClusterGroup.objects.all(),
        to_field_name="slug",
        label="Parent group (slug)",
    )
    type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ClusterType.objects.all(),
        label="Cluster type (ID)",
    )
    type = django_filters.ModelMultipleChoiceFilter(
        field_name="type__slug",
        queryset=ClusterType.objects.all(),
        to_field_name="slug",
        label="Cluster type (slug)",
    )
    tag = TagFilter()

    class Meta:
        model = Cluster
        fields = ["id", "name", "comments"]


class VirtualMachineFilterSet(
    NautobotFilterSet,
    LocalContextModelFilterSetMixin,
    TenancyModelFilterSetMixin,
    StatusModelFilterSetMixin,
):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "comments": "icontains",
        },
    )
    cluster_group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster__group",
        queryset=ClusterGroup.objects.all(),
        label="Cluster group (ID)",
    )
    cluster_group = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster__group__slug",
        queryset=ClusterGroup.objects.all(),
        to_field_name="slug",
        label="Cluster group (slug)",
    )
    cluster_type_id = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster__type",
        queryset=ClusterType.objects.all(),
        label="Cluster type (ID)",
    )
    cluster_type = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster__type__slug",
        queryset=ClusterType.objects.all(),
        to_field_name="slug",
        label="Cluster type (slug)",
    )
    cluster_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Cluster.objects.all(),
        label="Cluster (ID)",
    )
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="cluster__site__region",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="cluster__site__region",
        to_field_name="slug",
        label="Region (slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster__site",
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="cluster__site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site (slug)",
    )
    location = TreeNodeMultipleChoiceFilter(
        queryset=Location.objects.all(),
        field_name="cluster__location",
        to_field_name="slug",
        label="Location (slug or ID)",
    )
    role_id = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceRole.objects.all(),
        label="Role (ID)",
    )
    role = django_filters.ModelMultipleChoiceFilter(
        field_name="role__slug",
        queryset=DeviceRole.objects.all(),
        to_field_name="slug",
        label="Role (slug)",
    )
    platform_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Platform.objects.all(),
        label="Platform (ID)",
    )
    platform = django_filters.ModelMultipleChoiceFilter(
        field_name="platform__slug",
        queryset=Platform.objects.all(),
        to_field_name="slug",
        label="Platform (slug)",
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
        to_field_name="name", queryset=Service.objects.all(), label="Services (name or ID)"
    )
    has_services = RelatedMembershipBooleanFilter(
        field_name="services",
        label="Has services",
    )
    interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VMInterface.objects.all(), to_field_name="name", label="Interfaces (name or ID)"
    )
    has_interfaces = RelatedMembershipBooleanFilter(
        field_name="interfaces",
        label="Has interfaces",
    )
    tag = TagFilter()

    class Meta:
        model = VirtualMachine
        fields = ["id", "name", "cluster", "vcpus", "memory", "disk", "comments"]

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


class VMInterfaceFilterSet(BaseFilterSet, StatusModelFilterSetMixin, CustomFieldModelFilterSetMixin):
    q = SearchFilter(filter_predicates={"name": "icontains"})

    cluster_id = django_filters.ModelMultipleChoiceFilter(
        field_name="virtual_machine__cluster",
        queryset=Cluster.objects.all(),
        label="Cluster (ID)",
    )
    cluster = django_filters.ModelMultipleChoiceFilter(
        field_name="virtual_machine__cluster__name",
        queryset=Cluster.objects.all(),
        to_field_name="name",
        label="Cluster",
    )
    virtual_machine_id = django_filters.ModelMultipleChoiceFilter(
        field_name="virtual_machine",
        queryset=VirtualMachine.objects.all(),
        label="Virtual machine (ID)",
    )
    virtual_machine = django_filters.ModelMultipleChoiceFilter(
        field_name="virtual_machine__name",
        queryset=VirtualMachine.objects.all(),
        to_field_name="name",
        label="Virtual machine",
    )
    parent_interface = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=VMInterface.objects.all(),
        label="Parent interface (name or ID)",
    )
    child_interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=VMInterface.objects.all(),
        label="Child interfaces (name or ID)",
    )
    has_child_interfaces = RelatedMembershipBooleanFilter(
        field_name="child_interfaces",
        label="Has child interfaces",
    )
    bridge = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=VMInterface.objects.all(),
        label="Bridge interface (name or ID)",
    )
    bridged_interfaces = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=VMInterface.objects.all(),
        label="Bridged interfaces (name or ID)",
    )
    has_bridged_interfaces = RelatedMembershipBooleanFilter(
        field_name="bridged_interfaces",
        label="Has Bridged Interfaces",
    )
    mac_address = MultiValueMACAddressFilter(
        label="MAC address",
    )
    tagged_vlans = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="vid",
        queryset=VLAN.objects.all(),
        label="Tagged VLANs (VID or ID)",
    )
    has_tagged_vlans = RelatedMembershipBooleanFilter(
        field_name="tagged_vlans",
        label="Has Tagged VLANs",
    )
    untagged_vlan = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="vid",
        queryset=VLAN.objects.all(),
        label="Untagged VLAN (VID or ID)",
    )
    ip_addresses = MultiValueCharFilter(method="filter_ip_addresses", label="IP addresses (address or ID)")
    has_ip_addresses = RelatedMembershipBooleanFilter(field_name="ip_addresses", label="Has IP addresses")
    tag = TagFilter()

    def filter_ip_addresses(self, queryset, name, value):
        pk_values = set(item for item in value if is_uuid(item))
        addresses = set(item for item in value if item not in pk_values)

        ip_queryset = IPAddress.objects.filter_address_or_pk_in(addresses, pk_values)
        return queryset.filter(ip_addresses__in=ip_queryset)

    class Meta:
        model = VMInterface
        fields = ["id", "name", "description", "enabled", "mtu", "mode"]
