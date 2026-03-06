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
                        link="extras:fileproxy_list",
                        name="File Proxies",
                        weight=420,
                        permissions=["extras.view_fileproxy"],
                    ),
                ),
            ),
        ),
    ),
)
