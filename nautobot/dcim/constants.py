from django.db.models import Q

from .choices import InterfaceTypeChoices

#
# Racks
#

RACK_U_HEIGHT_DEFAULT = 42
RACK_U_HEIGHT_MAXIMUM = 500

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

COPPER_TWISTED_PAIR_IFACE_TYPES = [
    InterfaceTypeChoices.TYPE_100ME_FIXED,
    InterfaceTypeChoices.TYPE_1GE_FIXED,
    InterfaceTypeChoices.TYPE_2GE_FIXED,
    InterfaceTypeChoices.TYPE_5GE_FIXED,
    InterfaceTypeChoices.TYPE_10GE_FIXED,
]

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

# Maximum number of distinct connectors/lanes in a breakout cable
CABLE_BREAKOUT_MAX_CONNECTORS = 16
CABLE_BREAKOUT_MAX_LANES = 256

BREAKOUT_COMPATIBLE_TERMINATION_TYPES = frozenset(
    {
        "consoleport",
        "consoleserverport",
        "circuittermination",
        "frontport",
        "interface",
        "rearport",
    }
)

# AOC Ethernet Breakouts (strands_per_lane=1)
# Fiber MPO Fanouts (strands_per_lane=2, duplex)
DEFAULT_CABLE_BREAKOUT_TYPES = {
    # ── AOC Ethernet Breakouts ──
    "1x2 AOC Fanout": {
        "description": "1 trunk connector broken out to 2 individual legs",
        "a_connectors": 1,
        "b_connectors": 2,
        "total_lanes": 2,
        "mapping": [
            {"label": "1", "a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1},
            {"label": "2", "a_connector": 1, "a_position": 2, "b_connector": 2, "b_position": 1},
        ],
        "strands_per_lane": 1,
        "polarity_method": "",
        "is_shuffle": False,
    },
    "1x4 AOC Fanout": {
        "description": "1 trunk connector broken out to 4 individual legs",
        "a_connectors": 1,
        "b_connectors": 4,
        "total_lanes": 4,
        "mapping": [
            {"label": str(i), "a_connector": 1, "a_position": i, "b_connector": i, "b_position": 1} for i in range(1, 5)
        ],
        "strands_per_lane": 1,
        "polarity_method": "",
        "is_shuffle": False,
    },
    "1x8 AOC Fanout": {
        "description": "1 trunk connector broken out to 8 individual legs",
        "a_connectors": 1,
        "b_connectors": 8,
        "total_lanes": 8,
        "mapping": [
            {"label": str(i), "a_connector": 1, "a_position": i, "b_connector": i, "b_position": 1} for i in range(1, 9)
        ],
        "strands_per_lane": 1,
        "polarity_method": "",
        "is_shuffle": False,
    },
    "2x4 AOC Fanout": {
        "description": "2 trunk connectors (4 lanes each) broken out to 8 individual legs",
        "a_connectors": 2,
        "b_connectors": 8,
        "total_lanes": 8,
        "mapping": [
            {"label": "1", "a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1},
            {"label": "2", "a_connector": 1, "a_position": 2, "b_connector": 2, "b_position": 1},
            {"label": "3", "a_connector": 1, "a_position": 3, "b_connector": 3, "b_position": 1},
            {"label": "4", "a_connector": 1, "a_position": 4, "b_connector": 4, "b_position": 1},
            {"label": "5", "a_connector": 2, "a_position": 1, "b_connector": 5, "b_position": 1},
            {"label": "6", "a_connector": 2, "a_position": 2, "b_connector": 6, "b_position": 1},
            {"label": "7", "a_connector": 2, "a_position": 3, "b_connector": 7, "b_position": 1},
            {"label": "8", "a_connector": 2, "a_position": 4, "b_connector": 8, "b_position": 1},
        ],
        "strands_per_lane": 1,
        "polarity_method": "",
        "is_shuffle": False,
    },
    # ── Fiber MPO Fanouts ──
    "MPO-8 → 4xLC Duplex": {
        "description": "MPO-8 trunk fanning out to 4 LC duplex connections",
        "a_connectors": 1,
        "b_connectors": 4,
        "total_lanes": 4,
        "mapping": [
            {"label": str(i), "a_connector": 1, "a_position": i, "b_connector": i, "b_position": 1} for i in range(1, 5)
        ],
        "strands_per_lane": 2,
        "polarity_method": "straight-through",
        "is_shuffle": False,
    },
    "MPO-12 → 6xLC Duplex": {
        "description": "MPO-12 trunk fanning out to 6 LC duplex connections",
        "a_connectors": 1,
        "b_connectors": 6,
        "total_lanes": 6,
        "mapping": [
            {"label": str(i), "a_connector": 1, "a_position": i, "b_connector": i, "b_position": 1} for i in range(1, 7)
        ],
        "strands_per_lane": 2,
        "polarity_method": "straight-through",
        "is_shuffle": False,
    },
    "MPO-24 → 12xLC Duplex": {
        "description": "MPO-24 trunk fanning out to 12 LC duplex connections",
        "a_connectors": 1,
        "b_connectors": 12,
        "total_lanes": 12,
        "mapping": [
            {"label": str(i), "a_connector": 1, "a_position": i, "b_connector": i, "b_position": 1}
            for i in range(1, 13)
        ],
        "strands_per_lane": 2,
        "polarity_method": "straight-through",
        "is_shuffle": False,
    },
    "MPO-24 → 2xMPO-12": {
        "description": "MPO-24 trunk split into 2 MPO-12 trunks (6 lanes each)",
        "a_connectors": 1,
        "b_connectors": 2,
        "total_lanes": 12,
        "mapping": [
            # A1 positions 1-6 → B1 positions 1-6
            *[
                {"label": str(i), "a_connector": 1, "a_position": i, "b_connector": 1, "b_position": i}
                for i in range(1, 7)
            ],
            # A1 positions 7-12 → B2 positions 1-6
            *[
                {"label": str(i + 6), "a_connector": 1, "a_position": i + 6, "b_connector": 2, "b_position": i}
                for i in range(1, 7)
            ],
        ],
        "strands_per_lane": 2,
        "polarity_method": "straight-through",
        "is_shuffle": False,
    },
    "2xMPO-12 → 12xLC Duplex": {
        "description": "2 MPO-12 trunks (6 lanes each) fanning out to 12 LC duplex connections",
        "a_connectors": 2,
        "b_connectors": 12,
        "total_lanes": 12,
        "mapping": [
            # A1 positions 1-6 → B connectors 1-6
            *[
                {"label": str(i), "a_connector": 1, "a_position": i, "b_connector": i, "b_position": 1}
                for i in range(1, 7)
            ],
            # A2 positions 1-6 → B connectors 7-12
            *[
                {"label": str(i + 6), "a_connector": 2, "a_position": i, "b_connector": i + 6, "b_position": 1}
                for i in range(1, 7)
            ],
        ],
        "strands_per_lane": 2,
        "polarity_method": "straight-through",
        "is_shuffle": False,
    },
}

#
# Modules
#

# Limit of 4 allows recursion depth of Device->ModuleBay->Module->ModuleBay->Module->ModuleBay->Module->ModuleBay->Module
MODULE_RECURSION_DEPTH_LIMIT = 4

#
# Devices
#

# Limit of 4 allows recursion depth of Device->DeviceBay->Device->DeviceBay->Device->DeviceBay->Device->DeviceBay->Device
# Matches MODULE_RECURSION_DEPTH_LIMIT for consistency
DEVICE_RECURSION_DEPTH_LIMIT = 4
