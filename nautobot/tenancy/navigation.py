from nautobot.extras.nautobot_app import NavMenuButton, NavMenuItem, NavMenuTab, NavMenuGroup
from nautobot.utilities.choices import ButtonColorChoices


menu_tabs = (
    NavMenuTab(
        name="Organization",
        weight=100,
        groups= (
            NavMenuGroup(
                name="Tenancy",
                weight=300,
                items=(
                    NavMenuItem(
                        link="tenancy:tenant_list",
                        link_text="Tenants",
                        permissions=["",],
                    ),
                    NavMenuItem(
                        link="tenancy:tenantgroup_list",
                        link_text="Tenant Group",
                        permissions=["",],
                    ),
                ),
            ),
        ),
    ),
)
