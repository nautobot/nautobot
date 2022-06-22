from nautobot.core.apps import HomePageItem, HomePagePanel
from nautobot.ipam.models import Aggregate, IPAddress, Prefix, VLAN, VRF


layout = (
    HomePagePanel(
        name="IPAM",
        weight=400,
        items=(
            HomePageItem(
                name="VRFs",
                link="ipam:vrf_list",
                model=VRF,
                description="Virtual routing and forwarding tables",
                permissions=["ipam.view_vrf"],
                weight=100,
            ),
            HomePageItem(
                name="Aggregates",
                link="ipam:aggregate_list",
                model=Aggregate,
                description="Top-level IP allocations",
                permissions=["ipam.view_aggregate"],
                weight=200,
            ),
            HomePageItem(
                name="Prefixes",
                link="ipam:prefix_list",
                model=Prefix,
                description="IPv4 and IPv6 network assignments",
                permissions=["ipam.view_prefix"],
                weight=300,
            ),
            HomePageItem(
                name="IP Addresses",
                link="ipam:ipaddress_list",
                model=IPAddress,
                description="IPv4 and IPv6 network assignments",
                permissions=["ipam.view_ipaddress"],
                weight=400,
            ),
            HomePageItem(
                name="VLAN",
                link="ipam:vlan_list",
                model=VLAN,
                description="Layer two domains, identified by VLAN ID",
                permissions=["ipam.view_vlan"],
                weight=500,
            ),
        ),
    ),
)
