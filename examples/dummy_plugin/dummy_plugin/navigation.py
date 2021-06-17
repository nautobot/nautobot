from nautobot.core.apps import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuImportButton, NavMenuTab
from nautobot.extras.plugins import PluginMenuButton, PluginMenuItem
from nautobot.utilities.choices import ButtonColorChoices


menu_items = (
    PluginMenuItem(
        link="plugins:dummy_plugin:dummymodel_list",
        link_text="Models",
        buttons=(
            PluginMenuButton(
                link="plugins:dummy_plugin:dummymodel_add",
                title="Add a new dummy model",
                icon_class="mdi mdi-plus-thick",
                color=ButtonColorChoices.GREEN,
            ),
            PluginMenuButton(
                link="plugins:dummy_plugin:dummymodel_import",
                title="Import dummy models",
                icon_class="mdi mdi-database-import-outline",
                color=ButtonColorChoices.DEFAULT,
            ),
        ),
    ),
    PluginMenuItem(
        link="plugins:dummy_plugin:dummymodel_add",
        link_text="Other Models",
    ),
    NavMenuTab(
        name="Dummy Tab",
        weight=150,
        groups=(
            NavMenuGroup(
                name="Dummy Group 1",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:dummy_plugin:dummymodel_list",
                        link_text="Dummy Model",
                        permissions=["dummy_plugin.view_dummymodel"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:dummy_plugin:dummymodel_add",
                                permissions=[
                                    "dummy_plugin.add_dummymodel",
                                ],
                            ),
                            NavMenuImportButton(
                                link="plugins:dummy_plugin:dummymodel_import",
                                permissions=["dummy_plugin.add_dummymodel"],
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
                name="Dummy Circuit Group",
                weight=150,
                items=(
                    NavMenuItem(
                        link="plugins:dummy_plugin:dummymodel_list",
                        link_text="Dummy Model",
                        permissions=["dummy_plugin.view_dummymodel"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:dummy_plugin:dummymodel_add",
                                permissions=[
                                    "dummy_plugin.add_dummymodel",
                                ],
                            ),
                            NavMenuImportButton(
                                link="plugins:dummy_plugin:dummymodel_import",
                                permissions=["dummy_plugin.add_dummymodel"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
