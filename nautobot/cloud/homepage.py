from nautobot.cloud.models import CloudAccount, CloudNetwork, CloudType
from nautobot.core.apps import HomePageItem, HomePagePanel

layout = (
    HomePagePanel(
        name="Cloud",
        weight=500,
        items=(
            HomePageItem(
                name="Cloud Accounts",
                link="cloud:cloudaccount_list",
                model=CloudAccount,
                description="Account tracking for public and private cloud providers",
                permissions=["cloud.view_cloudaccount"],
                weight=400,
            ),
            HomePageItem(
                name="Cloud Types",
                link="cloud:cloudtype_list",
                model=CloudType,
                description="Types for public and private cloud providers",
                permissions=["cloud.view_cloudtype"],
                weight=300,
            ),
            HomePageItem(
                name="Cloud Networks",
                link="cloud:cloudnetwork_list",
                model=CloudNetwork,
                description="Networks for public and private cloud providers",
                permissions=["cloud.view_cloudnetwork"],
                weight=100,
            ),
        ),
    ),
)
