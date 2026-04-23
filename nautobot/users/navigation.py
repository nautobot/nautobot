from nautobot.core.apps import (
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)
from nautobot.core.ui.choices import NavigationIconChoices, NavigationWeightChoices

menu_items = (
    NavMenuTab(
        name="Administration",
        icon=NavigationIconChoices.ADMINISTRATION,
        weight=NavigationWeightChoices.ADMINISTRATION,
        groups=(
            NavMenuGroup(
                name="Administration",
                weight=100,
                items=(
                    NavMenuItem(
                        link="users:objectpermission_list",
                        name="Permissions",
                        weight=100,
                        permissions=["users.view_objectpermission"],
                    ),
                ),
            ),
        ),
    ),
)
