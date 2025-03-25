from nautobot.core.apps import HomePageItem, HomePagePanel
from nautobot.vpn.models import VPN

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
        ),
    ),
)
