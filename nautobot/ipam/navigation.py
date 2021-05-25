from nautobot.extras.nautobot_app import NavMenuButton, NavMenuItem, NavMenuTab, NavMenuGroup
from nautobot.utilities.choices import ButtonColorChoices


menu_tabs = (
    NavMenuTab(
        name="IPAM",
        weight=300,
        groups=(
            NavMenuGroup(
                name="IP Addresses",
                weight=100,
                items=(
                    NavMenuItem(
                        link="ipam:ipaddress_list",
                        link_text="IP Addresses",
                        permissions=[
                            "ipam.view_ipaddress",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="ipam:ipaddress_add",
                                title="IP Addresses",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "ipam.add_ipaddress",
                                ],
                            ),
                            NavMenuButton(
                                link="ipam:ipaddress_import",
                                title="IP Addresses",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "ipam.add_ipaddress",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Prefixes",
                weight=200,
                items=(
                    NavMenuItem(
                        link="ipam:prefix_list",
                        link_text="Prefixes",
                        permissions=[
                            "ipam.view_prefix",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="ipam:prefix_add",
                                title="Prefixes",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "ipam.add_prefix",
                                ],
                            ),
                            NavMenuButton(
                                link="ipam:prefix_import",
                                title="Prefixes",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "ipam.add_prefix",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="ipam:role_list",
                        link_text="Prefix/VLAN Roles",
                        permissions=[
                            "ipam.view_role",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="ipam:role_add",
                                title="Prefix/VLAN Roles",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "ipam.add_role",
                                ],
                            ),
                            NavMenuButton(
                                link="ipam:role_import",
                                title="Prefix/VLAN Roles",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "ipam.add_role",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Aggregates",
                weight=300,
                items=(
                    NavMenuItem(
                        link="ipam:aggregate_list",
                        link_text="Aggregates",
                        permissions=[
                            "ipam.view_aggregate",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="ipam:aggregate_add",
                                title="Aggregates",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "ipam.add_aggregate",
                                ],
                            ),
                            NavMenuButton(
                                link="ipam:aggregate_import",
                                title="Aggregates",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "ipam.add_aggregate",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="ipam:rir_list",
                        link_text="RIRs",
                        permissions=[
                            "ipam.view_rir",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="ipam:rir_add",
                                title="RIRs",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "ipam.add_rir",
                                ],
                            ),
                            NavMenuButton(
                                link="ipam:rir_import",
                                title="RIRs",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "ipam.add_rir",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="VRFs",
                weight=400,
                items=(
                    NavMenuItem(
                        link="ipam:vrf_list",
                        link_text="VRFs",
                        permissions=[
                            "ipam.view_vrf",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="ipam:vrf_add",
                                title="VRFs",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "ipam.add_vrf",
                                ],
                            ),
                            NavMenuButton(
                                link="ipam:vrf_import",
                                title="VRFs",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "ipam.add_vrf",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="ipam:routetarget_list",
                        link_text="Route Targets",
                        permissions=[
                            "ipam.view_routetarget",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="ipam:routetarget_add",
                                title="Route Targets",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "ipam.add_routetarget",
                                ],
                            ),
                            NavMenuButton(
                                link="ipam:routetarget_import",
                                title="Route Targets",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "ipam.add_routetarget",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="VLANs",
                weight=500,
                items=(
                    NavMenuItem(
                        link="ipam:vlan_list",
                        link_text="VLANs",
                        permissions=[
                            "ipam.view_vlan",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="ipam:vlan_add",
                                title="VLANs",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "ipam.add_vlan",
                                ],
                            ),
                            NavMenuButton(
                                link="ipam:vlan_import",
                                title="VLANs",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "ipam.add_vlan",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="ipam:vlangroup_list",
                        link_text="VLAN Groups",
                        permissions=[
                            "ipam.view_vlangroup",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="ipam:vlangroup_add",
                                title="VLAN Groups",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "ipam.add_vlangroup",
                                ],
                            ),
                            NavMenuButton(
                                link="ipam:vlangroup_import",
                                title="VLAN Groups",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "ipam.add_vlangroup",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Services",
                weight=600,
                items=(
                    NavMenuItem(
                        link="ipam:service_list",
                        link_text="Services",
                        permissions=[
                            "ipam.view_service",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="ipam:service_import",
                                title="Services",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "ipam.add_service",
                                ],
                            ),
                        ),
                    ),
                ),
            )
        ),
    ),
)