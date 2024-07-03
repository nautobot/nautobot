from nautobot.core.apps import (
    NavMenuAddButton,
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)

menu_items = (
    NavMenuTab(
        name="Cloud",
        weight=200,
        groups=(
            NavMenuGroup(
                name="Accounts",
                weight=100,
                items=(
                    NavMenuItem(
                        link="cloud:cloudaccount_list",
                        name="Cloud Accounts",
                        weight=100,
                        permissions=[
                            "cloud.view_cloudaccount",
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="cloud:cloudaccount_add",
                                permissions=[
                                    "cloud.add_cloudaccount",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="cloud:cloudtype_list",
                        name="Cloud Types",
                        weight=200,
                        permissions=[
                            "cloud.view_cloudtype",
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="cloud:cloudtype_add",
                                permissions=[
                                    "cloud.add_cloudtype",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)