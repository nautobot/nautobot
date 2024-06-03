from nautobot.core.apps import (
    NavContext,
    NavGrouping,
    NavItem,
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
                ),
            ),
        ),
    ),
)

navigation = (
    NavContext(
        name="Inventory",
        groups=(
            NavGrouping(
                name="Cloud",
                weight=400,
                items=(
                    NavItem(
                        link="cloud:cloudaccount_list",
                        name="Cloud Accounts",
                        weight=100,
                        permissions=[
                            "cloud.view_cloudaccount",
                        ],
                    ),
                ),
            ),
        ),
    ),
)
