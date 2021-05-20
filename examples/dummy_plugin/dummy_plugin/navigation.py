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
                color=ButtonColorChoices.GREEN
            ),
            PluginMenuButton(
                link="plugins:dummy_plugin:dummymodel_import",
                title="Import dummy models",
                icon_class="mdi mdi-database-import-outline",
                color=ButtonColorChoices.DEFAULT
            ),
        ),
    ),
    PluginMenuItem(
        link="plugins:dummy_plugin:dummymodel_list",
        link_text="Other Models",
    ),
)
