from nautobot.core.apps import HomePageItem, HomePagePanel
from nautobot.vpn.models import VPN, VPNTunnel, VPNTunnelEndpoint

layout = (
    HomePagePanel(
        name="VPN",
        weight=550,
        items=(
            HomePageItem(
                name="VPNs",
                link="vpn:vpn_list",
                model=VPN,
                description="VPNs",
                permissions=["vpn.view_vpn"],
                weight=100,
            ),
            HomePageItem(
                name="VPN Tunnels",
                link="vpn:vpntunnel_list",
                model=VPNTunnel,
                description="VPN Tunnels",
                permissions=["vpn.view_vpntunnel"],
                weight=200,
            ),
            HomePageItem(
                name="VPN Tunnel Endpoints",
                link="vpn:vpntunnelendpoint_list",
                model=VPNTunnelEndpoint,
                description="VPN Tunnel Endpoints",
                permissions=["vpn.view_vpntunnelendpoint"],
                weight=300,
            ),
        ),
    ),
)
