from nautobot.core.apps import (
    NavContext,
    NavGrouping,
    NavItem,
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)

menu_items = (
    NavMenuTab(
        name="Users",
        weight=1000,
        groups=(
            NavMenuGroup(
                name="Users",
                weight=100,
                items=(
                    NavMenuItem(
                        link="users:savedview_list",
                        name="Saved Views",
                        weight=100,
                        permissions=["users.view_savedviews"],
                    ),
                ),
            ),
        ),
    ),
)

navigation = (
    NavContext(
        name="Platform",
        groups=(
            NavGrouping(
                name="Users",
                weight=400,
                items=(
                    NavItem(
                        link="users:savedview_list",
                        name="Saved Views",
                        weight=100,
                        permissions=["users.view_savedviews"],
                    ),
                ),
            ),
        ),
    ),
)
