from nautobot.core.apps import HomePageGroup, HomePageItem, HomePagePanel
from nautobot.dcim import models


layout = (
    HomePagePanel(
        name="Organization",
        weight=100,
        items=(
            HomePageItem(
                name="Sites",
                link="dcim:site_list",
                model=models.Site,
                description="Geographic location",
                permissions=["dcim.view_site"],
                weight=100,
            ),
        ),
    ),
    HomePagePanel(
        name="DCIM",
        weight=200,
        items=(
            HomePageItem(
                name="Racks",
                link="dcim:rack_list",
                model=models.Rack,
                description="Equipment racks, optionally organized by group",
                permissions=["dcim.view_rack"],
                weight=100,
            ),
            HomePageItem(
                name="Device Types",
                link="dcim:devicetype_list",
                model=models.DeviceType,
                description="Physical hardware models by manufacturer",
                permissions=["dcim.view_devicetype"],
                weight=200,
            ),
            HomePageItem(
                name="Devices",
                link="dcim:device_list",
                model=models.Device,
                description="Rack-mounted network equipment, servers, and other devices",
                permissions=["dcim.view_device"],
                weight=300,
            ),
            HomePageItem(
                name="Virtual Chassis",
                link="dcim:virtualchassis_list",
                model=models.VirtualChassis,
                permissions=["dcim.view_virtualchassis"],
                description="Represents a set of devices which share a common control plane",
                weight=400,
            ),
            HomePageGroup(
                name="Connections",
                weight=500,
                items=(
                    HomePageItem(
                        name="Cables",
                        link="dcim:cable_list",
                        model=models.Cable,
                        permissions=["dcim.view_cable"],
                        weight=100,
                    ),
                    HomePageItem(
                        name="Interfaces",
                        link="dcim:interface_connections_list",
                        model=models.Interface,
                        permissions=["dcim.view_interface"],
                        weight=200,
                    ),
                    HomePageItem(
                        name="Console",
                        link="dcim:console_connections_list",
                        model=models.ConsolePort,
                        permissions=["dcim.view_consoleport", "dcim.view_consoleserverport"],
                        weight=300,
                    ),
                    HomePageItem(
                        name="Power",
                        link="dcim:power_connections_list",
                        model=models.PowerOutlet,
                        permissions=["dcim.view_powerport", "dcim.view_poweroutlet"],
                        weight=400,
                    ),
                ),
            ),
        ),
    ),
    HomePagePanel(
        name="Power",
        weight=300,
        items=(
            HomePageItem(
                name="Power Feeds",
                link="dcim:powerfeed_list",
                model=models.PowerFeed,
                description="Electrical circuits delivering power from panels",
                permissions=["dcim.view_powerfeed"],
                weight=100,
            ),
            HomePageItem(
                name="Power Panels",
                link="dcim:powerpanel_list",
                model=models.PowerPanel,
                description="Electrical panels receiving utility power",
                permissions=["dcim.view_powerpanel"],
                weight=200,
            ),
        ),
    ),
)
