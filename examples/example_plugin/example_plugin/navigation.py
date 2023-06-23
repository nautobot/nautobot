from nautobot.apps.ui import (
    NavMenuAddButton,
    NavMenuGroup,
    NavMenuItem,
    NavMenuImportButton,
    NavMenuTab,
)


menu_items = (
    NavMenuTab(
        name="Plugins",
        groups=(
            NavMenuGroup(
                name="Example Nautobot App",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:example_plugin:examplemodel_list",
                        name="Models",
                        permissions=["example_plugin.view_examplemodel"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:example_plugin:examplemodel_add",
                                permissions=[
                                    "example_plugin.add_examplemodel",
                                ],
                            ),
                            NavMenuImportButton(
                                link="plugins:example_plugin:examplemodel_import",
                                permissions=["example_plugin.add_examplemodel"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:example_plugin:anotherexamplemodel_list",
                        name="Other Models",
                        permissions=["example_plugin.view_anotherexamplemodel"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:example_plugin:anotherexamplemodel_add",
                                permissions=[
                                    "example_plugin.add_anotherexamplemodel",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
    NavMenuTab(
        name="Example Menu",
        groups=(
            NavMenuGroup(
                name="Example Group 1",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:example_plugin:examplemodel_list",
                        name="Example Model",
                        permissions=["example_plugin.view_examplemodel"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:example_plugin:examplemodel_add",
                                permissions=[
                                    "example_plugin.add_examplemodel",
                                ],
                            ),
                            NavMenuImportButton(
                                link="plugins:example_plugin:examplemodel_import",
                                permissions=["example_plugin.add_examplemodel"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
    NavMenuTab(
        name="Circuits",
        groups=(
            NavMenuGroup(
                name="Example Circuit Group",
                weight=150,
                items=(
                    NavMenuItem(
                        link="plugins:example_plugin:examplemodel_list",
                        name="Example Model",
                        permissions=["example_plugin.view_examplemodel"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:example_plugin:examplemodel_add",
                                permissions=[
                                    "example_plugin.add_examplemodel",
                                ],
                            ),
                            NavMenuImportButton(
                                link="plugins:example_plugin:examplemodel_import",
                                permissions=["example_plugin.add_examplemodel"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
