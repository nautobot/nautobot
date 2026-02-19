from nautobot.core.apps import (
    NavMenuAddButton,
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
                        link="users:token_list",
                        name="Tokens",
                        weight=100,
                        permissions=[
                            "users.view_token",
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="users:token_add",
                                permissions=[
                                    "users.add_token",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
