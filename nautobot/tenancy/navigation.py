from nautobot.core.apps import NavMenuGroup, NavMenuItem, NavMenuTab


menu_items = (
    NavMenuTab(
        name="Inventory",
        groups=(
            NavMenuGroup(
                name="Tenancy",
                weight=300,
                items=(
                    NavMenuItem(
                        name="Tenants",
                        weight=100,
                        link="tenancy:tenant_list",
                        permissions=["tenancy.view_tenant"],
                    ),
                    NavMenuItem(
                        name="Tenant Groups",
                        weight=200,
                        link="tenancy:tenantgroup_list",
                        permissions=["tenancy.view_tenantgroup"],
                    ),
                ),
            ),
        ),
    ),
)
