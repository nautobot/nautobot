from nautobot.core.apps import HomePageItem, HomePagePanel
from nautobot.wireless.models import AccessPointGroup, RadioProfile, SupportedDataRate, WirelessNetwork

layout = (
    HomePagePanel(
        name="Wireless",
        weight=500,
        items=(
            HomePageItem(
                name="Access Point Groups",
                link="wireless:accesspointgroup_list",
                model=AccessPointGroup,
                description="Groups of access points managed by a controller",
                permissions=["wireless.view_accesspointgroup"],
                weight=100,
            ),
            HomePageItem(
                name="Radio Profiles",
                link="wireless:radioprofile_list",
                model=RadioProfile,
                description="Profiles for configuring radio settings",
                permissions=["wireless.view_radioprofile"],
                weight=200,
            ),
            HomePageItem(
                name="Supported Data Rates",
                link="wireless:supporteddatarate_list",
                model=SupportedDataRate,
                description="Supported data rates for wireless networks",
                permissions=["wireless.view_supporteddatarate"],
                weight=300,
            ),
            HomePageItem(
                name="Wireless Networks",
                link="wireless:wirelessnetwork_list",
                model=WirelessNetwork,
                description="Wireless networks for access points",
                permissions=["wireless.view_wirelessnetwork"],
                weight=400,
            ),
        )
    ),
),

