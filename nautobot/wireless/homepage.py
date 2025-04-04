from nautobot.core.apps import HomePageItem, HomePagePanel
from nautobot.wireless.models import WirelessNetwork

layout = (
    HomePagePanel(
        name="Wireless",
        weight=500,
        items=(
            HomePageItem(
                name="Wireless Networks",
                link="wireless:wirelessnetwork_list",
                model=WirelessNetwork,
                description="Wireless networks for access points",
                permissions=["wireless.view_wirelessnetwork"],
                weight=100,
            ),
        ),
    ),
)
