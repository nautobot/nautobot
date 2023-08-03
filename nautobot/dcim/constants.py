from django.db.models import Q

from .choices import InterfaceTypeChoices


#
# Racks
#

RACK_U_HEIGHT_DEFAULT = 42

RACK_ELEVATION_BORDER_WIDTH = 2
RACK_ELEVATION_LEGEND_WIDTH_DEFAULT = 30


#
# RearPorts
#

REARPORT_POSITIONS_MIN = 1
REARPORT_POSITIONS_MAX = 1024


#
# Interfaces
#

INTERFACE_MTU_MIN = 1
INTERFACE_MTU_MAX = 32767  # Max value of a signed 16-bit integer

VIRTUAL_IFACE_TYPES = [
    InterfaceTypeChoices.TYPE_VIRTUAL,
    InterfaceTypeChoices.TYPE_BRIDGE,
    InterfaceTypeChoices.TYPE_LAG,
]

WIRELESS_IFACE_TYPES = [
    InterfaceTypeChoices.TYPE_80211A,
    InterfaceTypeChoices.TYPE_80211G,
    InterfaceTypeChoices.TYPE_80211N,
    InterfaceTypeChoices.TYPE_80211AC,
    InterfaceTypeChoices.TYPE_80211AD,
]

NONCONNECTABLE_IFACE_TYPES = VIRTUAL_IFACE_TYPES + WIRELESS_IFACE_TYPES


#
# PowerFeeds
#

POWERFEED_VOLTAGE_DEFAULT = 120

POWERFEED_AMPERAGE_DEFAULT = 20

POWERFEED_MAX_UTILIZATION_DEFAULT = 80  # Percentage


#
# Cabling and connections
#

# Cable endpoint types
CABLE_TERMINATION_MODELS = Q(
    Q(app_label="circuits", model__in=("circuittermination",))
    | Q(
        app_label="dcim",
        model__in=(
            "consoleport",
            "consoleserverport",
            "frontport",
            "interface",
            "powerfeed",
            "poweroutlet",
            "powerport",
            "rearport",
        ),
    )
)

COMPATIBLE_TERMINATION_TYPES = {
    "circuittermination": ["interface", "frontport", "rearport", "circuittermination"],
    "consoleport": ["consoleserverport", "frontport", "rearport"],
    "consoleserverport": ["consoleport", "frontport", "rearport"],
    "interface": ["interface", "circuittermination", "frontport", "rearport"],
    "frontport": [
        "consoleport",
        "consoleserverport",
        "interface",
        "frontport",
        "rearport",
        "circuittermination",
    ],
    "powerfeed": ["powerport"],
    "poweroutlet": ["powerport"],
    "powerport": ["poweroutlet", "powerfeed"],
    "rearport": [
        "consoleport",
        "consoleserverport",
        "interface",
        "frontport",
        "rearport",
        "circuittermination",
    ],
}

#
# Platforms
#

NETUTILS_NETWORK_DRIVER_MAPPING_NAMES = {
    "ansible",
    "hier_config",
    "napalm",
    "netmiko",
    "ntc_templates",
    "pyats",
    "pyntc",
    "scrapli",
}
