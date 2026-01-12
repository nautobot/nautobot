from nautobot.core.apps import (
    NavMenuAddButton,
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)
from nautobot.core.ui.choices import NavigationIconChoices, NavigationWeightChoices

menu_items = (
    NavMenuTab(
        name="Organization",
        icon=NavigationIconChoices.ORGANIZATION,
        weight=NavigationWeightChoices.ORGANIZATION,
        groups=(
            NavMenuGroup(
                name="Tenancy",
                weight=300,
                items=(
                    NavMenuItem(
                        link="tenancy:tenant_list",
                        name="Tenants",
                        weight=100,
                        permissions=[
                            "tenancy.view_tenant",
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="tenancy:tenant_add",
                                permissions=[
                                    "tenancy.add_tenant",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="tenancy:tenantgroup_list",
                        name="Tenant Groups",
                        weight=200,
                        permissions=[
                            "tenancy.view_tenantgroup",
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="tenancy:tenantgroup_add",
                                permissions=[
                                    "tenancy.add_tenantgroup",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
