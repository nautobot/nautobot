from nautobot.core.apps import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuImportButton, NavMenuTab
from nautobot.extras.plugins import PluginMenuButton, PluginMenuItem
from nautobot.utilities.choices import ButtonColorChoices


menu_items = (
    PluginMenuItem(
        link="plugins:example_plugin:examplemodel_list",
        link_text="Models",
        permissions=["example_plugin.view_examplemodel"],
        buttons=(
            PluginMenuButton(
                link="plugins:example_plugin:examplemodel_add",
                title="Add a new example model",
                icon_class="mdi mdi-plus-thick",
                color=ButtonColorChoices.GREEN,
                permissions=[
                    "example_plugin.add_examplemodel",
                ],
            ),
            PluginMenuButton(
                link="plugins:example_plugin:examplemodel_import",
                title="Import example models",
                icon_class="mdi mdi-database-import-outline",
                color=ButtonColorChoices.DEFAULT,
                permissions=[
                    "example_plugin.add_examplemodel",
                ],
            ),
        ),
    ),
    PluginMenuItem(
        link="plugins:example_plugin:examplemodel_add",
        link_text="Other Models",
        permissions=["example_plugin.view_examplemodel"],
    ),
    NavMenuTab(
        name="Example Menu",
        weight=150,
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
