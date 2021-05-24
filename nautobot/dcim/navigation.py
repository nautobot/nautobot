from nautobot.extras.nautobot_app import NavMenuButton, NavMenuItem, NavMenuTab, NavMenuGroup
from nautobot.utilities.choices import ButtonColorChoices


menu_tabs = (
    NavMenuTab(
        name="Organization",
        weight=100,
        groups= (
            NavMenuGroup(
                name="Sites",
                weight=100,
                items=(
                    NavMenuItem(
                        link="dcim:site_list",
                        link_text="Sites",
                        permissions=["",],
                        buttons=(
                            NavMenuButton(
                                link="dcim:site_add",
                                title="Sites",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=["dcim.add_site",],
                            ),
                            NavMenuButton(
                                link="dcim:site_add",
                                title="Sites",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=["dcim.add_site",],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:region_list",
                        link_text="Regions",
                        permissions=["",],
                        buttons=(
                            NavMenuButton(
                                link="dcim:region_add",
                                title="Regions",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=["dcim.add_region",],
                            ),
                            NavMenuButton(
                                link="dcim:region_add",
                                title="Regions",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=["dcim.add_region",],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
