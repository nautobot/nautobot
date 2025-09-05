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

interface_type_by_category = {}
for category_name, category_item_tuples in InterfaceTypeChoices.CHOICES:
    interface_type_by_category[category_name] = [item_tuple[0] for item_tuple in category_item_tuples]

WIRELESS_IFACE_TYPES = interface_type_by_category["Wireless"]
VIRTUAL_IFACE_TYPES = interface_type_by_category["Virtual interfaces"]

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
# Modules
#

# Limit of 4 allows recursion depth of Device->ModuleBay->Module->ModuleBay->Module->ModuleBay->Module->ModuleBay->Module
MODULE_RECURSION_DEPTH_LIMIT = 4
