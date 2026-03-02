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
                        link="users:user_list",
                        name="Users",
                        weight=430,
                        permissions=["users.view_user"],
                    ),
                ),
            ),
        ),
    ),
)
