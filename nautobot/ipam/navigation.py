from nautobot.core.apps import NavMenuGroup, NavMenuItem, NavMenuTab


menu_items = (
    NavMenuTab(
        name="Networks",
        groups=(
            NavMenuGroup(
                name="IP Management",
                weight=100,
                items=(
                    NavMenuItem(
                        name="IP Addresses",
                        weight=100,
                        link="ipam:ipaddress_list",
                        permissions=["ipam.view_ipaddress"],
                    ),
                    NavMenuItem(
                        name="Prefixes",
                        weight=200,
                        link="ipam:prefix_list",
                        permissions=["ipam.view_prefix"],
                    ),
                    NavMenuItem(
                        name="RIRs",
                        weight=300,
                        link="ipam:rir_list",
                        permissions=["ipam.view_rir"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Layer 2 / Switching",
                weight=200,
                items=(
                    NavMenuItem(
                        name="VLANs",
                        weight=100,
                        link="ipam:vlan_list",
                        permissions=["ipam.view_vlan"],
                    ),
                    NavMenuItem(
                        name="VLAN Groups",
                        weight=200,
                        link="ipam:vlangroup_list",
                        permissions=["ipam.view_vlangroup"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Layer 3 / Routing",
                weight=300,
                items=(
                    NavMenuItem(
                        name="Namespaces",
                        weight=100,
                        link="ipam:namespace_list",
                        permissions=["ipam.view_namespace"],
                    ),
                    NavMenuItem(
                        name="VRFs",
                        weight=200,
                        link="ipam:vrf_list",
                        permissions=["ipam.view_vrf"],
                    ),
                    NavMenuItem(
                        name="Route Targets",
                        weight=300,
                        link="ipam:routetarget_list",
                        permissions=["ipam.view_routetarget"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Services",
                weight=400,
                items=(
                    NavMenuItem(
                        name="Services",
                        weight=100,
                        link="ipam:service_list",
                        permissions=["ipam.view_service"],
                    ),
                ),
            ),
        ),
    ),
)
