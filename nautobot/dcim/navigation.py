from nautobot.core.apps import NavMenuGroup, NavMenuItem, NavMenuTab


menu_items = (
    NavMenuTab(
        name="Inventory",
        weight=100,
        groups=(
            NavMenuGroup(
                name="Devices",
                weight=100,
                items=(
                    NavMenuItem(
                        name="Devices",
                        link="dcim:device_list",
                        weight=100,
                        permissions=["dcim.view_device"],
                    ),
                    NavMenuItem(
                        name="Device Types",
                        weight=200,
                        link="dcim:devicetype_list",
                        permissions=["dcim.view_devicetype"],
                    ),
                    NavMenuItem(
                        link="dcim:platform_list",
                        name="Platforms",
                        weight=300,
                        permissions=[
                            "dcim.view_platform",
                        ],
                    ),
                    NavMenuItem(
                        link="dcim:manufacturer_list",
                        name="Manufacturers",
                        weight=400,
                        permissions=[
                            "dcim.view_manufacturer",
                        ],
                    ),
                    NavMenuItem(
                        link="dcim:virtualchassis_list",
                        name="Virtual Chassis",
                        weight=500,
                        permissions=[
                            "dcim.view_virtualchassis",
                        ],
                    ),
                    NavMenuItem(
                        name="Device Redundancy Groups",
                        weight=600,
                        link="dcim:deviceredundancygroup_list",
                        permissions=["dcim.view_deviceredundancygroup"],
                    ),
                    NavMenuGroup(
                        name="Connections",
                        weight=700,
                        items=(
                            NavMenuItem(
                                name="Cables",
                                weight=100,
                                link="dcim:cable_list",
                                permissions=["dcim.view_cable"],
                            ),
                            NavMenuItem(
                                name="Console Connections",
                                weight=200,
                                link="dcim:console_connections_list",
                                permissions=[
                                    "dcim.view_consoleport",
                                    "dcim.view_consoleserverport",
                                ],
                            ),
                            NavMenuItem(
                                name="Power Connections",
                                weight=300,
                                link="dcim:power_connections_list",
                                permissions=[
                                    "dcim.view_powerport",
                                    "dcim.view_poweroutlet",
                                ],
                            ),
                            NavMenuItem(
                                name="Interface Connections",
                                weight=400,
                                link="dcim:interface_connections_list",
                                permissions=["dcim.view_interface"],
                            ),
                        ),
                    ),
                    NavMenuGroup(
                        name="Components",
                        weight=800,
                        items=(
                            NavMenuItem(
                                name="Interfaces",
                                weight=100,
                                link="dcim:interface_list",
                                permissions=["dcim.view_interface"],
                            ),
                            NavMenuItem(
                                name="Front Ports",
                                weight=200,
                                link="dcim:frontport_list",
                                permissions=["dcim.view_frontport"],
                            ),
                            NavMenuItem(
                                name="Rear Ports",
                                weight=300,
                                link="dcim:rearport_list",
                                permissions=["dcim.view_rearport"],
                            ),
                            NavMenuItem(
                                name="Console Ports",
                                weight=400,
                                link="dcim:consoleport_list",
                                permissions=["dcim.view_consoleport"],
                            ),
                            NavMenuItem(
                                name="Console Server Ports",
                                weight=500,
                                link="dcim:consoleserverport_list",
                                permissions=["dcim.view_consoleserverport"],
                            ),
                            NavMenuItem(
                                name="Power Ports",
                                weight=600,
                                link="dcim:powerport_list",
                                permissions=["dcim.view_powerport"],
                            ),
                            NavMenuItem(
                                name="Power Outlets",
                                weight=700,
                                link="dcim:poweroutlet_list",
                                permissions=["dcim.view_poweroutlet"],
                            ),
                            NavMenuItem(
                                name="Device Bays",
                                weight=800,
                                link="dcim:devicebay_list",
                                permissions=["dcim.view_devicebay"],
                            ),
                            NavMenuItem(
                                name="Inventory Items",
                                weight=900,
                                link="dcim:inventoryitem_list",
                                permissions=["dcim.view_inventoryitem"],
                            ),
                        ),
                    ),
                    # space reserved for Dynamic Groups item with weight 900
                    NavMenuItem(
                        name="Racks",
                        weight=1000,
                        link="dcim:rack_list",
                        permissions=["dcim.view_rack"],
                    ),
                    NavMenuItem(
                        name="Rack Groups",
                        weight=1100,
                        link="dcim:rackgroup_list",
                        permissions=["dcim.view_rackgroup"],
                    ),
                    NavMenuItem(
                        name="Rack Reservations",
                        weight=1200,
                        link="dcim:rackreservation_list",
                        permissions=["dcim.view_rackreservation"],
                    ),
                    NavMenuItem(
                        name="Rack Elevations",
                        weight=1300,
                        link="dcim:rack_elevation_list",
                        permissions=["dcim.view_rack"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Organization",
                weight=200,
                items=(
                    NavMenuItem(
                        link="dcim:location_list",
                        name="Locations",
                        weight=100,
                        permissions=[
                            "dcim.view_location",
                        ],
                    ),
                    NavMenuItem(
                        link="dcim:locationtype_list",
                        name="Location Types",
                        weight=200,
                        permissions=[
                            "dcim.view_locationtype",
                        ],
                    ),
                ),
            ),
            # space reserved for Tenants at weight 300
            # space reserved for Circuits at weight 400
            NavMenuGroup(
                name="Power",
                weight=500,
                items=(
                    NavMenuItem(
                        name="Power Feeds",
                        link="dcim:powerfeed_list",
                        weight=100,
                        permissions=["dcim.view_powerfeed"],
                    ),
                    NavMenuItem(
                        name="Power Panels",
                        weight=200,
                        link="dcim:powerpanel_list",
                        permissions=["dcim.view_powerpanel"],
                    ),
                ),
            ),
        ),
    ),
)
