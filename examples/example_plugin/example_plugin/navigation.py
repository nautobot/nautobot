from nautobot.apps.ui import (
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)


menu_items = (
    NavMenuTab(
        name="Inventory",
        groups=(
            NavMenuGroup(
                name="Example App",
                weight=150,
                items=(
                    NavMenuItem(
                        name="Example Model",
                        weight=100,
                        link="plugins:example_plugin:examplemodel_list",
                        permissions=["example_plugin.view_examplemodel"],
                    ),
                ),
            ),
        ),
    ),
)
