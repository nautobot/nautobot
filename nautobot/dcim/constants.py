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

DEVICE_COMPONENT_ICONS = {
    "circuittermination": "mdi-cable-data",
    "consoleport": "mdi-console",
    "consoleporttemplate": "mdi-console",
    "consoleserverport": "mdi-console-network-outline",
    "consoleserverporttemplate": "mdi-console-network-outline",
    "devicebay": "mdi-circle-outline",  # DeviceDeviceBayTable overrides -> mdi-circle-slice-8 for populated bays
    "devicebaytemplate": "mdi-circle-outline",
    "frontport": "mdi-arrow-right-bold-box-outline",
    "frontporttemplate": "mdi-arrow-right-bold-box-outline",
    "interface": "mdi-ethernet",
    "interfacetemplate": "mdi-ethernet",
    "inventoryitem": "mdi-invoice-list-outline",
    "modulebay": "mdi-tray",  # DeviceModuleBayTable overrides -> mdi-expansion-card-variant for populated bays
    "modulebaytemplate": "mdi-tray",
    "powerfeed": "mdi-flash",
    "poweroutlet": "mdi-power-socket",
    "poweroutlettemplate": "mdi-power-socket",
    "powerport": "mdi-power-plug-outline",
    "powerporttemplate": "mdi-power-plug-outline",
    "rearport": "mdi-arrow-left-bold-box-outline",
    "rearporttemplate": "mdi-arrow-left-bold-box-outline",
}

CABLE_TERMINATION_GENERIC_ICON = "mdi-cable-data"

# Maps each cable-termination type to the list of types its other end may connect to. List order is
# significant: the first entry is used as the default B-side type when creating a cable from a given
# A-side type (see `CableForm._init_lane_fields`), so each list should lead with the most natural /
# most common peer for that termination type.
COMPATIBLE_TERMINATION_TYPES = {
    "circuittermination": ["interface", "frontport", "rearport", "circuittermination"],
    "consoleport": ["consoleserverport", "frontport", "rearport"],
    "consoleserverport": ["consoleport", "frontport", "rearport"],
    "interface": ["interface", "circuittermination", "frontport", "rearport"],
    "frontport": [
        "interface",
        "frontport",
        "rearport",
        "circuittermination",
        "consoleport",
        "consoleserverport",
    ],
    "powerfeed": ["powerport"],
    "poweroutlet": ["powerport"],
    "powerport": ["poweroutlet", "powerfeed"],
    "rearport": [
        "interface",
        "frontport",
        "rearport",
        "circuittermination",
        "consoleport",
        "consoleserverport",
    ],
}

# Maximum number of distinct connectors/lanes in a breakout cable
CABLE_BREAKOUT_MAX_CONNECTORS = 16
CABLE_BREAKOUT_MAX_LANES = 256

BREAKOUT_COMPATIBLE_TERMINATION_TYPES = frozenset(
    {
        "circuittermination",
        "frontport",
        "interface",
        "rearport",
    }
)

# Per-type one-to-one FK field name on `CableToCableTermination` → ContentType natural key
# (app_label, model) for its target model. At most one of these FKs may be non-null on each row;
# enforced by a CheckConstraint on the model. The "exactly one" stricter requirement is enforced
# in `clean()` — at the DB level the all-null state is allowed because Django's cascade-delete
# machinery temporarily nulls the nullable FK before deleting the row, and a CHECK constraint
# would block that intermediate step on MySQL.
TERMINATION_FK_TO_CONTENT_TYPE = {
    "circuit_termination": ("circuits", "circuittermination"),
    "console_port": ("dcim", "consoleport"),
    "console_server_port": ("dcim", "consoleserverport"),
    "front_port": ("dcim", "frontport"),
    "interface": ("dcim", "interface"),
    "power_feed": ("dcim", "powerfeed"),
    "power_outlet": ("dcim", "poweroutlet"),
    "power_port": ("dcim", "powerport"),
    "rear_port": ("dcim", "rearport"),
}
TERMINATION_FK_FIELDS = tuple(TERMINATION_FK_TO_CONTENT_TYPE)
# Reverse map: ContentType natural key (app_label, model) → FK field name. Used by signal /
# form / serializer code that needs to write to the right per-type FK given a termination instance.
CONTENT_TYPE_TO_TERMINATION_FK = {ct: fk for fk, ct in TERMINATION_FK_TO_CONTENT_TYPE.items()}

# Per-type FK field on `CableToCableTermination` → the FK on that termination model that resolves
# its `parent` (e.g. an Interface's parent is its `device`, a CircuitTermination's is its `circuit`,
# a PowerFeed's is its `power_panel`). Used to extend `select_related` so that rendering
# `termination.parent` for cable / cable-peer / connection columns stays query-free per row.
TERMINATION_FK_TO_PARENT_FK = {
    "circuit_termination": "circuit",
    "console_port": "device",
    "console_server_port": "device",
    "front_port": "device",
    "interface": "device",
    "power_feed": "power_panel",
    "power_outlet": "device",
    "power_port": "device",
    "rear_port": "device",
}
# `select_related` paths joining each termination through to its parent, e.g. "interface__device".
TERMINATION_PARENT_FK_FIELDS = tuple(
    f"{termination_fk}__{parent_fk}" for termination_fk, parent_fk in TERMINATION_FK_TO_PARENT_FK.items()
)

# Extra `select_related` paths needed to render a termination's display string without a query.
# Only `CircuitTermination` has a non-trivial `__str__` — it names its location / provider network /
# cloud network — so those FKs must be joined; every other termination renders as its (already
# loaded) name.
TERMINATION_DISPLAY_FK_FIELDS = (
    "circuit_termination__location",
    "circuit_termination__provider_network",
    "circuit_termination__cloud_network",
)

# Everything a `CableToCableTermination` row needs `select_related` so that rendering each mapped
# termination's cable columns — the termination itself, its `parent`, and its display string — is
# query-free. Use this wherever `cable.terminations` is prefetched for table / detail renders.
TERMINATION_CABLE_COLUMN_FK_FIELDS = (
    *TERMINATION_FK_FIELDS,
    *TERMINATION_PARENT_FK_FIELDS,
    *TERMINATION_DISPLAY_FK_FIELDS,
)

# AOC Ethernet Breakouts (strands_per_lane=1)
# Fiber MPO Fanouts (strands_per_lane=2, duplex)
DEFAULT_CABLE_TYPES = {
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
        "has_embedded_transceivers": True,
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
        "has_embedded_transceivers": True,
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
        "has_embedded_transceivers": True,
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
        "has_embedded_transceivers": True,
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
