from nautobot.core.apps import (
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)
from nautobot.core.ui.choices import NavigationIconChoices, NavigationWeightChoices

menu_items = (
    NavMenuTab(
        name="ADMINISTRATION",
        icon=NavigationIconChoices.ADMINISTRATION,
        weight=NavigationWeightChoices.ADMINISTRATION,
        groups=(
            NavMenuGroup(
                name="Authentication",
                weight=100,
                items=(
                    NavMenuItem(
                        link="user:logentry_list",
                        name="Log Entries",
                        weight=100,
                        permissions=["users.view_logentry"],
                        buttons=(),
                    ),
                ),
            ),
        ),
    ),
)
