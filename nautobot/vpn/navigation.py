"""Menu items."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab

menu_items = (
    NavMenuTab(
        name="Plugins",  # TODO INIT change this if you want the app to have its own tab in the navbar
        groups=(
            NavMenuGroup(
                name="Nautobot Vpn Models",  # TODO INIT you will likely want to change this.
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_vpn_models:vpnprofile_list",
                        name="VPN Profiles",  # TODO INIT Verify.
                        weight=100,  # TODO INIT The standard is to have these listed in reverse order of creation, changing the weight will influence the order.
                        permissions=["nautobot_vpn_models.view_vpnprofile"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_vpn_models:vpnprofile_add",
                                permissions=["nautobot_vpn_models.add_vpnprofile"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_vpn_models:vpnphase1policy_list",
                        name="VPN Phase 1 Policys",  # TODO INIT Verify.
                        weight=100,  # TODO INIT The standard is to have these listed in reverse order of creation, changing the weight will influence the order.
                        permissions=["nautobot_vpn_models.view_vpnphase1policy"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_vpn_models:vpnphase1policy_add",
                                permissions=["nautobot_vpn_models.add_vpnphase1policy"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_vpn_models:vpnphase2policy_list",
                        name="VPN Phase 2 Policys",  # TODO INIT Verify.
                        weight=100,  # TODO INIT The standard is to have these listed in reverse order of creation, changing the weight will influence the order.
                        permissions=["nautobot_vpn_models.view_vpnphase2policy"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_vpn_models:vpnphase2policy_add",
                                permissions=["nautobot_vpn_models.add_vpnphase2policy"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_vpn_models:vpn_list",
                        name="VPNs",  # TODO INIT Verify.
                        weight=100,  # TODO INIT The standard is to have these listed in reverse order of creation, changing the weight will influence the order.
                        permissions=["nautobot_vpn_models.view_vpn"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_vpn_models:vpn_add",
                                permissions=["nautobot_vpn_models.add_vpn"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_vpn_models:vpntunnel_list",
                        name="VPN Tunnels",  # TODO INIT Verify.
                        weight=100,  # TODO INIT The standard is to have these listed in reverse order of creation, changing the weight will influence the order.
                        permissions=["nautobot_vpn_models.view_vpntunnel"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_vpn_models:vpntunnel_add",
                                permissions=["nautobot_vpn_models.add_vpntunnel"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_vpn_models:vpntunnelendpoint_list",
                        name="VPN Tunnel Endpoints",  # TODO INIT Verify.
                        weight=100,  # TODO INIT The standard is to have these listed in reverse order of creation, changing the weight will influence the order.
                        permissions=["nautobot_vpn_models.view_vpntunnelendpoint"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_vpn_models:vpntunnelendpoint_add",
                                permissions=["nautobot_vpn_models.add_vpntunnelendpoint"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)