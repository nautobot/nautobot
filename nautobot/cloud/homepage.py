from nautobot.cloud.models import CloudAccount, CloudNetwork, CloudResourceType, CloudService
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
                weight=100,
            ),
            HomePageItem(
                name="Cloud Resource Types",
                link="cloud:cloudresourcetype_list",
                model=CloudResourceType,
                description="Resource types for public and private cloud providers",
                permissions=["cloud.view_cloudresourcetype"],
                weight=200,
            ),
            HomePageItem(
                name="Cloud Networks",
                link="cloud:cloudnetwork_list",
                model=CloudNetwork,
                description="Networks for public and private cloud providers",
                permissions=["cloud.view_cloudnetwork"],
                weight=300,
            ),
            HomePageItem(
                name="Cloud Services",
                link="cloud:cloudservice_list",
                model=CloudService,
                description="Services for public and private cloud providers",
                permissions=["cloud.view_cloudservice"],
                weight=400,
            ),
        ),
    ),
)
