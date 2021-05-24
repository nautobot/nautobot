from nautobot.extras.nautobot_app import NavMenuButton, NavMenuItem, NavMenuTab, NavMenuGroup
from nautobot.utilities.choices import ButtonColorChoices


menu_tabs = (
    NavMenuTab(
        name="Organization",
        weight=100,
        groups= (
            NavMenuGroup(
                name="Tags",
                weight=600,
                items=(
                    NavMenuItem(
                        link="extras:tag_list",
                        link_text="Tags",
                        permissions=["",],
                        buttons=(
                            NavMenuButton(
                                link="extras:tag_add",
                                title="Tags",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=["extras.add_tag",],
                            ),
                            NavMenuButton(
                                link="extras:tag_add",
                                title="Tags",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=["extras.add_tag",],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
