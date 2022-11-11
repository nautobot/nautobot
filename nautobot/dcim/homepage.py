from django.contrib.contenttypes.models import ContentType
from django.db.models import F

from nautobot.core.apps import HomePageGroup, HomePageItem, HomePagePanel
from nautobot.dcim import models


def _connected_consoleports_count(request):
    # Match queryset used in dcim.views.ConsoleConnectionsListView
    return models.ConsolePort.objects.restrict(request.user, "view").filter(_path__isnull=False).count()


def _connected_interfaces_count(request):
    # Match queryset used in dcim.views.InterfaceConnectionsListView
    return (
        models.Interface.objects.restrict(request.user, "view")
        .filter(_path__isnull=False)
        .exclude(
            _path__destination_type=ContentType.objects.get_for_model(models.Interface),
            pk__lt=F("_path__destination_id"),
        )
        .count()
    )


def _connected_powerports_count(request):
    # Match queryset used in dcim.views.PowerConnectionsListView
    return models.PowerPort.objects.restrict(request.user, "view").filter(_path__isnull=False).count()


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
            HomePageItem(
                name="Locations",
                link="dcim:location_list",
                model=models.Location,
                description="Hierarchical geographic locations",
                permissions=["dcim.view_location"],
                weight=200,
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
            HomePageItem(
                name="Device Redundancy Groups",
                link="dcim:deviceredundancygroup_list",
                model=models.DeviceRedundancyGroup,
                permissions=["dcim.view_deviceredundancygroup"],
                description="Represents a set of devices which operate in a failover/HA group",
                weight=500,
            ),
            HomePageGroup(
                name="Connections",
                weight=600,
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
                        custom_template="homepage_connections.html",
                        custom_data={
                            "connections_count": _connected_interfaces_count,
                            "connections_url": "dcim:interface_connections_list",
                            "connections_label": "Interfaces",
                        },
                        permissions=["dcim.view_interface"],
                        weight=200,
                    ),
                    HomePageItem(
                        name="Console",
                        custom_template="homepage_connections.html",
                        custom_data={
                            "connections_count": _connected_consoleports_count,
                            "connections_url": "dcim:console_connections_list",
                            "connections_label": "Console",
                        },
                        permissions=["dcim.view_consoleport", "dcim.view_consoleserverport"],
                        weight=300,
                    ),
                    HomePageItem(
                        name="Power",
                        custom_template="homepage_connections.html",
                        custom_data={
                            "connections_count": _connected_powerports_count,
                            "connections_url": "dcim:power_connections_list",
                            "connections_label": "Power",
                        },
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
