from nautobot.cloud.models import CloudAccount
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
        ),
    ),
)
