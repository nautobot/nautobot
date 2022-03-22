from nautobot.core.apps import HomePageItem, HomePagePanel
from nautobot.tenancy.models import Tenant


layout = (
    HomePagePanel(
        name="Organization",
        weight=100,
        items=(
            HomePageItem(
                name="Tenants",
                link="tenancy:tenant_list",
                model=Tenant,
                description="Customers or departments",
                permissions=["tenancy.view_tenant"],
                weight=200,
            ),
        ),
    ),
)
