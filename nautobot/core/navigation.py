from nautobot.core.apps import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab


# TODO fix initialization order issue with admin site
_menu_items = (
    NavMenuTab(
        name="Organization",
        weight=100,
        groups=(
            NavMenuGroup(
                name="Dynamic Groups",
                weight=500,
                items=(
                    NavMenuItem(
                        link="core:dynamicgroup_list",
                        name="Dynamic Groups",
                        weight=100,
                        permissions=[
                            "core.view_dynamicgroup",
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="core:dynamicgroup_add",
                                permissions=[
                                    "core.add_dynamicgroup",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
