from nautobot.extras.nautobot_app import NavMenuButton, NavMenuItem, NavMenuTab, NavMenuGroup
from nautobot.utilities.choices import ButtonColorChoices


menu_tabs = (
    NavMenuTab(
        name="Organization",
        weight=100,
        groups=(
            NavMenuGroup(
                name="Sites",
                weight=100,
                items=(
                    NavMenuItem(
                        link="dcim:site_list",
                        link_text="Sites",
                        permissions=[
                            "dcim.view_site",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:site_add",
                                title="Sites",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_site",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:site_add",
                                title="Sites",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_site",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:region_list",
                        link_text="Regions",
                        permissions=[
                            "dcim.view_region",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:region_add",
                                title="Regions",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_region",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:region_add",
                                title="Regions",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_region",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Racks",
                weight=200,
                items=(
                    NavMenuItem(
                        link="dcim:rack_list",
                        link_text="Racks",
                        permissions=[
                            "dcim.view_rack",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:rack_add",
                                title="Racks",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_rack",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:rack_import",
                                title="Racks",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_rack",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:rackgroup_list",
                        link_text="Rack Groups",
                        permissions=[
                            "dcim.view_rackgroup",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:rackgroup_add",
                                title="Racks Groups",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_rackgroup",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:rackgroup_import",
                                title="Racks Groups",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_rackgroup",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:rackrole_list",
                        link_text="Rack Roles",
                        permissions=[
                            "dcim.view_rackrole",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:rackrole_add",
                                title="Racks Roles",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_rackrole",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:rackrole_import",
                                title="Racks Roles",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_rackrole",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:rackreservation_list",
                        link_text="Reservations",
                        permissions=[
                            "dcim.view_rackreservation",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:rackreservation_add",
                                title="Racks Reservations",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_rackreservation",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:rackreservation_import",
                                title="Racks Reservations",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_rackreservation",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:rack_elevation_list",
                        link_text="Elevations",
                        permissions=[
                            "dcim.view_elevation",
                        ],
                        buttons=(),
                    ),
                ),
            ),
        ),
    ),
    NavMenuTab(
        name="Devices",
        weight=200,
        groups=(
            NavMenuGroup(
                name="Devices",
                weight=100,
                items=(
                    NavMenuItem(
                        link="dcim:device_list",
                        link_text="Devices",
                        permissions=[
                            "dcim.view_device",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:device_add",
                                title="Devices",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_device",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:device_import",
                                title="Devices",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_device",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:devicerole_list",
                        link_text="Device Roles",
                        permissions=[
                            "dcim.view_devicerole",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:devicerole_add",
                                title="Device Roles",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_devicerole",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:devicerole_import",
                                title="Device Roles",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_devicerole",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:platform_list",
                        link_text="Platforms",
                        permissions=[
                            "dcim.view_platform",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:platform_add",
                                title="Platforms",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_platform",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:platform_import",
                                title="Platforms",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_platform",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:virtualchassis_list",
                        link_text="Virtual Chassis",
                        permissions=[
                            "dcim.view_virtualchassis",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:virtualchassis_add",
                                title="Virtual Chassis",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_virtualchassis",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:virtualchassis_import",
                                title="Virtual Chassis",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_virtualchassis",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Device Types",
                weight=200,
                items=(
                    NavMenuItem(
                        link="dcim:devicetype_list",
                        link_text="Device Types",
                        permissions=[
                            "dcim.view_devicetype",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:devicetype_add",
                                title="Device Types",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_devicetype",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:devicetype_import",
                                title="Device Types",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_devicetype",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:manufacturer_list",
                        link_text="Manufacturer",
                        permissions=[
                            "dcim.view_manufacturer",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:manufacturer_add",
                                title="Manufacturer",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_manufacturer",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:manufacturer_import",
                                title="Manufacturer",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_manufacturer",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Connections",
                weight=300,
                items=(
                    NavMenuItem(
                        link="dcim:cable_list",
                        link_text="Cables",
                        permissions=[
                            "dcim.view_cable",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:cable_import",
                                title="Cables",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_cables",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:console_connections_list",
                        link_text="Console Connections",
                        permissions=[
                            "dcim.view_consoleport",
                            "dcim.view_consoleserverport",
                        ],
                        buttons=(),
                    ),
                    NavMenuItem(
                        link="dcim:power_connections_list",
                        link_text="Power Connections",
                        permissions=[
                            "dcim.view_powerport",
                            "dcim.view_poweroutlet",
                        ],
                        buttons=(),
                    ),
                    NavMenuItem(
                        link="dcim:interface_connections_list",
                        link_text="Interface Connections",
                        permissions=[
                            "dcim.view_interface",
                        ],
                        buttons=(),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Device Components",
                weight=400,
                items=(
                    NavMenuItem(
                        link="dcim:interface_list",
                        link_text="Interfaces",
                        permissions=[
                            "dcim.view_interface",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:interface_import",
                                title="Interfaces",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_interface",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:frontport_list",
                        link_text="Front Ports",
                        permissions=[
                            "dcim.view_frontport",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:frontport_import",
                                title="Front Ports",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_frontport",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:rearport_list",
                        link_text="Rear Ports",
                        permissions=[
                            "dcim.view_rearport",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:rearport_import",
                                title="Rear Ports",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_rearport",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:consoleport_list",
                        link_text="Console Ports",
                        permissions=[
                            "dcim.view_consoleport",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:consoleport_import",
                                title="Console Ports",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_consoleport",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:consoleport_list",
                        link_text="Console Server Ports",
                        permissions=[
                            "dcim.view_consoleserverport",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:consoleserverport_import",
                                title="Console Server Ports",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_serverport",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:powerport_list",
                        link_text="Power Ports",
                        permissions=[
                            "dcim.view_powerport",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:powerport_import",
                                title="Power Ports",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_powerport",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:poweroutlet_list",
                        link_text="Power Outlets",
                        permissions=[
                            "dcim.view_poweroutlet",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:poweroutlet_import",
                                title="Power Outlets",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_poweroutlet",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:devicebay_list",
                        link_text="Device Bays",
                        permissions=[
                            "dcim.view_devicebay",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:devicebay_import",
                                title="Device Bays",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_devicebay",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:inventoryitem_list",
                        link_text="Inventory Items",
                        permissions=[
                            "dcim.view_inventoryitem",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:inventoryitem_import",
                                title="Inventory Items",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_inventoryitem",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
    NavMenuTab(
        name="Power",
        weight=600,
        groups=(
            NavMenuGroup(
                name="Power",
                weight=100,
                items=(
                    NavMenuItem(
                        link="dcim:powerfeed_list",
                        link_text="Power Feeds",
                        permissions=[
                            "dcim.view_powerfeed",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:powerfeed_add",
                                title="Power Feeds",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_powerfeed",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:powerfeed_import",
                                title="Power Feeds",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_powerfeed",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:powerpanel_list",
                        link_text="Power Panels",
                        permissions=[
                            "dcim.view_powerpanel",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="dcim:powerpanel_add",
                                title="Power Panels",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "dcim.add_powerpanel",
                                ],
                            ),
                            NavMenuButton(
                                link="dcim:powerpanel_import",
                                title="Power Panels",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "dcim.add_powerpanel",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
