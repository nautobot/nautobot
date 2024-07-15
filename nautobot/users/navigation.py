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
        name="Extensibility",
        weight=900,
        groups=(
            NavMenuGroup(
                name="Users",
                weight=150,
                items=(
                    NavMenuItem(
                        link="extras:savedview_list",
                        name="Saved Views",
                        weight=100,
                        permissions=[
                            "extras.view_savedview",
                        ],
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
                weight=500,
                items=(
                    NavItem(
                        link="extras:savedview_list",
                        name="Saved Views",
                        weight=100,
                        permissions=["extras.view_savedviews"],
                    ),
                ),
            ),
        ),
    ),
)
