from collections import OrderedDict

from nautobot.circuits.filters import CircuitFilterSet, ProviderFilterSet, ProviderNetworkFilterSet
from nautobot.circuits.models import Circuit, Provider, ProviderNetwork
from nautobot.circuits.tables import CircuitTable, ProviderTable, ProviderNetworkTable
from nautobot.dcim.filters import (
    CableFilterSet,
    DeviceFilterSet,
    DeviceTypeFilterSet,
    PowerFeedFilterSet,
    RackFilterSet,
    RackGroupFilterSet,
    SiteFilterSet,
    VirtualChassisFilterSet,
)
from nautobot.dcim.models import (
    Cable,
    Device,
    DeviceType,
    PowerFeed,
    Rack,
    RackGroup,
    Site,
    VirtualChassis,
)
from nautobot.dcim.tables import (
    CableTable,
    DeviceTable,
    DeviceTypeTable,
    PowerFeedTable,
    RackTable,
    RackGroupTable,
    SiteTable,
    VirtualChassisTable,
)
from nautobot.ipam.filters import (
    AggregateFilterSet,
    IPAddressFilterSet,
    PrefixFilterSet,
    VLANFilterSet,
    VRFFilterSet,
)
from nautobot.ipam.models import Aggregate, IPAddress, Prefix, VLAN, VRF
from nautobot.ipam.tables import (
    AggregateTable,
    IPAddressTable,
    PrefixTable,
    VLANTable,
    VRFTable,
)
from nautobot.tenancy.filters import TenantFilterSet
from nautobot.tenancy.models import Tenant
from nautobot.tenancy.tables import TenantTable
from nautobot.utilities.utils import count_related
from nautobot.virtualization.filters import ClusterFilterSet, VirtualMachineFilterSet
from nautobot.virtualization.models import Cluster, VirtualMachine
from nautobot.virtualization.tables import ClusterTable, VirtualMachineDetailTable

SEARCH_MAX_RESULTS = 15
SEARCH_TYPES = OrderedDict(
    (
        # Circuits
        (
            "provider",
            {
                "queryset": Provider.objects.annotate(count_circuits=count_related(Circuit, "provider")),
                "filterset": ProviderFilterSet,
                "table": ProviderTable,
                "url": "circuits:provider_list",
            },
        ),
        (
            "circuit",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": Circuit.objects.prefetch_related("type", "provider", "tenant", "terminations__site"),
                "filterset": CircuitFilterSet,
                "table": CircuitTable,
                "url": "circuits:circuit_list",
            },
        ),
        (
            "providernetwork",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": ProviderNetwork.objects.prefetch_related("provider"),
                "filterset": ProviderNetworkFilterSet,
                "table": ProviderNetworkTable,
                "url": "circuits:providernetwork_list",
            },
        ),
        # DCIM
        (
            "site",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": Site.objects.prefetch_related("region", "tenant"),
                "filterset": SiteFilterSet,
                "table": SiteTable,
                "url": "dcim:site_list",
            },
        ),
        (
            "rack",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": Rack.objects.prefetch_related("site", "group", "tenant", "role"),
                "filterset": RackFilterSet,
                "table": RackTable,
                "url": "dcim:rack_list",
            },
        ),
        (
            "rackgroup",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": RackGroup.objects.add_related_count(
                    RackGroup.objects.all(),
                    Rack,
                    "group",
                    "rack_count",
                    cumulative=True,
                ).prefetch_related("site"),
                "filterset": RackGroupFilterSet,
                "table": RackGroupTable,
                "url": "dcim:rackgroup_list",
            },
        ),
        (
            "devicetype",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": DeviceType.objects.prefetch_related("manufacturer").annotate(
                    instance_count=count_related(Device, "device_type")
                ),
                "filterset": DeviceTypeFilterSet,
                "table": DeviceTypeTable,
                "url": "dcim:devicetype_list",
            },
        ),
        (
            "device",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": Device.objects.prefetch_related(
                    "device_type__manufacturer",
                    "device_role",
                    "tenant",
                    "site",
                    "rack",
                    "primary_ip4",
                    "primary_ip6",
                ),
                "filterset": DeviceFilterSet,
                "table": DeviceTable,
                "url": "dcim:device_list",
            },
        ),
        (
            "virtualchassis",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": VirtualChassis.objects.prefetch_related("master").annotate(
                    member_count=count_related(Device, "virtual_chassis")
                ),
                "filterset": VirtualChassisFilterSet,
                "table": VirtualChassisTable,
                "url": "dcim:virtualchassis_list",
            },
        ),
        (
            "cable",
            {
                "queryset": Cable.objects.all(),
                "filterset": CableFilterSet,
                "table": CableTable,
                "url": "dcim:cable_list",
            },
        ),
        (
            "powerfeed",
            {
                "queryset": PowerFeed.objects.all(),
                "filterset": PowerFeedFilterSet,
                "table": PowerFeedTable,
                "url": "dcim:powerfeed_list",
            },
        ),
        # Virtualization
        (
            "cluster",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": Cluster.objects.prefetch_related("type", "group").annotate(
                    device_count=count_related(Device, "cluster"),
                    vm_count=count_related(VirtualMachine, "cluster"),
                ),
                "filterset": ClusterFilterSet,
                "table": ClusterTable,
                "url": "virtualization:cluster_list",
            },
        ),
        (
            "virtualmachine",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": VirtualMachine.objects.prefetch_related(
                    "cluster",
                    "tenant",
                    "platform",
                    "primary_ip4",
                    "primary_ip6",
                ),
                "filterset": VirtualMachineFilterSet,
                "table": VirtualMachineDetailTable,
                "url": "virtualization:virtualmachine_list",
            },
        ),
        # IPAM
        (
            "vrf",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": VRF.objects.prefetch_related("tenant"),
                "filterset": VRFFilterSet,
                "table": VRFTable,
                "url": "ipam:vrf_list",
            },
        ),
        (
            "aggregate",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": Aggregate.objects.prefetch_related("rir"),
                "filterset": AggregateFilterSet,
                "table": AggregateTable,
                "url": "ipam:aggregate_list",
            },
        ),
        (
            "prefix",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": Prefix.objects.prefetch_related("site", "vrf__tenant", "tenant", "vlan", "role"),
                "filterset": PrefixFilterSet,
                "table": PrefixTable,
                "url": "ipam:prefix_list",
            },
        ),
        (
            "ipaddress",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": IPAddress.objects.prefetch_related("vrf__tenant", "tenant"),
                "filterset": IPAddressFilterSet,
                "table": IPAddressTable,
                "url": "ipam:ipaddress_list",
            },
        ),
        (
            "vlan",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": VLAN.objects.prefetch_related("site", "group", "tenant", "role"),
                "filterset": VLANFilterSet,
                "table": VLANTable,
                "url": "ipam:vlan_list",
            },
        ),
        # Tenancy
        (
            "tenant",
            {
                # v2 TODO(jathan): Replace prefetch_related with select_related
                "queryset": Tenant.objects.prefetch_related("group"),
                "filterset": TenantFilterSet,
                "table": TenantTable,
                "url": "tenancy:tenant_list",
            },
        ),
    )
)
