from nautobot.extras.nautobot_app import NavMenuButton, NavMenuItem, NavMenuTab, NavMenuGroup
from nautobot.utilities.choices import ButtonColorChoices


menu_tabs = (
    NavMenuTab(
        name="Organization",
        weight=100,
        groups=(
            NavMenuGroup(
                name="Tenancy",
                weight=300,
                items=(
                    NavMenuItem(
                        link="tenancy:tenant_list",
                        link_text="Tenants",
                        permissions=[
                            "tenancy.view_tenant",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="tenancy:tenant_add",
                                title="Tenants",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "tenancy.add_tag",
                                ],
                            ),
                            NavMenuButton(
                                link="tenancy:tenant_import",
                                title="Tenants",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "tenancy.add_tenant",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="tenancy:tenantgroup_list",
                        link_text="Tenant Group",
                        permissions=[
                            "tenancy.view_tenantgroup",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="tenancy:tenant_add",
                                title="Tenant Group",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "tenancy.add_tenant",
                                ],
                            ),
                            NavMenuButton(
                                link="tenancy:tenantgroup_import",
                                title="Tenant Group",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "tenancy.add_tenant",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
