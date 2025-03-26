"""Menu items for the vpn models."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab

menu_items = (
    NavMenuTab(
        name="VPN",  # TODO INIT change this if you want the app to have its own tab in the navbar
        weight=250,
        groups=(
            NavMenuGroup(
                name="VPN Models",  # TODO INIT you will likely want to change this.
                weight=100,
                items=(
                    NavMenuItem(
                        link="vpn:vpnprofile_list",
                        name="VPN Profiles",  # TODO INIT Verify.
                        weight=100,  # TODO INIT The standard is to have these listed in reverse order of creation, changing the weight will influence the order.
                        permissions=["vpn.view_vpnprofile"],
                        buttons=(
                            NavMenuAddButton(
                                link="vpn:vpnprofile_add",
                                permissions=["vpn.add_vpnprofile"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="vpn:vpnphase1policy_list",
                        name="VPN Phase 1 Policies",  # TODO INIT Verify.
                        weight=100,  # TODO INIT The standard is to have these listed in reverse order of creation, changing the weight will influence the order.
                        permissions=["vpn.view_vpnphase1policy"],
                        buttons=(
                            NavMenuAddButton(
                                link="vpn:vpnphase1policy_add",
                                permissions=["vpn.add_vpnphase1policy"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="vpn:vpnphase2policy_list",
                        name="VPN Phase 2 Policies",  # TODO INIT Verify.
                        weight=100,  # TODO INIT The standard is to have these listed in reverse order of creation, changing the weight will influence the order.
                        permissions=["vpn.view_vpnphase2policy"],
                        buttons=(
                            NavMenuAddButton(
                                link="vpn:vpnphase2policy_add",
                                permissions=["vpn.add_vpnphase2policy"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="vpn:vpn_list",
                        name="VPNs",  # TODO INIT Verify.
                        weight=100,  # TODO INIT The standard is to have these listed in reverse order of creation, changing the weight will influence the order.
                        permissions=["vpn.view_vpn"],
                        buttons=(
                            NavMenuAddButton(
                                link="vpn:vpn_add",
                                permissions=["vpn.add_vpn"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="vpn:vpntunnel_list",
                        name="VPN Tunnels",  # TODO INIT Verify.
                        weight=100,  # TODO INIT The standard is to have these listed in reverse order of creation, changing the weight will influence the order.
                        permissions=["vpn.view_vpntunnel"],
                        buttons=(
                            NavMenuAddButton(
                                link="vpn:vpntunnel_add",
                                permissions=["vpn.add_vpntunnel"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="vpn:vpntunnelendpoint_list",
                        name="VPN Tunnel Endpoints",  # TODO INIT Verify.
                        weight=100,  # TODO INIT The standard is to have these listed in reverse order of creation, changing the weight will influence the order.
                        permissions=["vpn.view_vpntunnelendpoint"],
                        buttons=(
                            NavMenuAddButton(
                                link="vpn:vpntunnelendpoint_add",
                                permissions=["vpn.add_vpntunnelendpoint"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
