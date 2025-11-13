"""Menu items for the vpn models."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab
from nautobot.core.ui.choices import NavigationIconChoices, NavigationWeightChoices

menu_items = (
    NavMenuTab(
        name="VPN",
        icon=NavigationIconChoices.VPN,
        weight=NavigationWeightChoices.VPN,
        groups=(
            NavMenuGroup(
                name="VPNs",
                weight=100,
                items=(
                    NavMenuItem(
                        link="vpn:vpn_list",
                        name="VPNs",
                        weight=100,
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
                        name="VPN Tunnels",
                        weight=100,
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
                        name="VPN Tunnel Endpoints",
                        weight=100,
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
            NavMenuGroup(
                name="Profiles & Policies",
                weight=100,
                items=(
                    NavMenuItem(
                        link="vpn:vpnprofile_list",
                        name="VPN Profiles",
                        weight=100,
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
                        name="VPN Phase 1 Policies",
                        weight=100,
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
                        name="VPN Phase 2 Policies",
                        weight=100,
                        permissions=["vpn.view_vpnphase2policy"],
                        buttons=(
                            NavMenuAddButton(
                                link="vpn:vpnphase2policy_add",
                                permissions=["vpn.add_vpnphase2policy"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
