# Generated migration: back-populate the root device FK on all modular component rows
# that are currently attached via a module only.
#
# Data model
# ----------
# dcim_modulebay:
#   parent_device_id  – set when the bay belongs directly to a device (top-level bay)
#   parent_module_id  – set when the bay belongs to a nested module
#
# dcim_module:
#   parent_module_bay_id – the bay this module is installed in (only parent link)
#
# ModularComponentModel subclasses (Interface, ConsolePort, ConsoleServerPort,
#   PowerPort, PowerOutlet, FrontPort, RearPort):
#   device_id  – root device shortcut (what we are filling)
#   module_id  – immediate parent module
#
# Hierarchy
# ---------
#   Device
#     └─ ModuleBay  [parent_device_id=<device>, parent_module_id=NULL]
#          └─ Module  [parent_module_bay_id=<bay>]
#               └─ ModuleBay  [parent_device_id=NULL, parent_module_id=<module>]
#                    └─ Module  [parent_module_bay_id=<bay>]
#                         └─ Interface / ConsolePort / etc.  [module_id=<module>]
#
# Strategy
# --------
# A single recursive CTE builds the map  module_id → root_device_id  by anchoring
# at top-level ModuleBays (parent_device_id IS NOT NULL) and walking down.
#
# That map is then used in two UPDATE shapes:
#   1. ModularComponentModel subclasses  – join on module_id,        write device_id
#   2. dcim_modulebay                    – join on parent_module_id, write parent_device_id

from django.db import migrations

# Tables using the standard ModularComponentModel columns (device_id / module_id)
MODULAR_COMPONENT_TABLES = [
    "dcim_consoleport",
    "dcim_consoleserverport",
    "dcim_powerport",
    "dcim_poweroutlet",
    "dcim_frontport",
    "dcim_rearport",
    "dcim_interface",
]

# ---------------------------------------------------------------------------
# Shared CTE
# ---------------------------------------------------------------------------
# Base case  : top-level ModuleBays have parent_device_id set directly.
#              Any Module installed in such a bay inherits that device.
#
# Recursive  : a child ModuleBay (parent_module_id = already-resolved module)
#              lets us reach the next Module installed in that bay, which also
#              inherits the same root_device_id.
#
# Join path each recursion level:
#   dcim_module.parent_module_bay_id  →  dcim_modulebay.id
#       (the bay this module sits inside)
#   dcim_modulebay.parent_module_id   →  dcim_module.id
#       (the module that owns/contains that bay — one level up)

_CTE = """\
WITH RECURSIVE module_device_map AS (

    -- Base case: modules installed in a top-level bay (bay owned by a device)
    SELECT
        m.id                  AS module_id,
        bay.parent_device_id  AS root_device_id
    FROM dcim_module    m
    JOIN dcim_modulebay bay ON bay.id = m.parent_module_bay_id
    WHERE bay.parent_device_id IS NOT NULL

    UNION ALL

    -- Recursive step: modules installed in a nested bay (bay owned by a module)
    SELECT
        m.id                     AS module_id,
        resolved.root_device_id
    FROM dcim_module        m
    JOIN dcim_modulebay     bay      ON bay.id              = m.parent_module_bay_id
    JOIN module_device_map  resolved ON resolved.module_id  = bay.parent_module_id
    WHERE bay.parent_device_id IS NULL

)
"""

# UPDATE for ModularComponentModel subclasses
_UPDATE_COMPONENT = (
    _CTE
    + """\
UPDATE {table}
SET    device_id = mdm.root_device_id
FROM   module_device_map mdm
WHERE  {table}.module_id  = mdm.module_id
  AND  {table}.device_id IS NULL;
"""
)

# UPDATE for ModuleBay (different column names)
_UPDATE_MODULE_BAY = (
    _CTE
    + """\
UPDATE dcim_modulebay
SET    parent_device_id = mdm.root_device_id
FROM   module_device_map mdm
WHERE  dcim_modulebay.parent_module_id  = mdm.module_id
  AND  dcim_modulebay.parent_device_id IS NULL;
"""
)

# ---------------------------------------------------------------------------
# Reverse SQL
# ---------------------------------------------------------------------------

_REVERSE_COMPONENT = """\
UPDATE {table}
SET    device_id = NULL
WHERE  module_id IS NOT NULL;
"""

_REVERSE_MODULE_BAY = """\
UPDATE dcim_modulebay
SET    parent_device_id = NULL
WHERE  parent_module_id IS NOT NULL;
"""


# ---------------------------------------------------------------------------
# Migration functions
# ---------------------------------------------------------------------------


def backpopulate_device(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for table in MODULAR_COMPONENT_TABLES:
            cursor.execute(_UPDATE_COMPONENT.format(table=table))
        cursor.execute(_UPDATE_MODULE_BAY)


def clear_backpopulated_device(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for table in MODULAR_COMPONENT_TABLES:
            cursor.execute(_REVERSE_COMPONENT.format(table=table))
        cursor.execute(_REVERSE_MODULE_BAY)


# ---------------------------------------------------------------------------
# Migration class
# ---------------------------------------------------------------------------


class Migration(migrations.Migration):
    """
    Data migration: back-populate the root device FK on modular components.

    Before applying:
      1. Replace the dependency below with the actual latest dcim migration in
         your branch, e.g. ("dcim", "0070_my_previous_migration").
      2. Run ANALYZE on dcim_module and dcim_modulebay beforehand so the query
         planner has fresh statistics for the recursive CTE joins.
      3. The UPDATE on dcim_interface (215M+ rows) will hold row-level locks for
         its duration. Plan for a maintenance window, or batch the interface
         update separately with keyset pagination if zero-downtime is required.
      4. Partial indexes will significantly speed up the joins into target tables:
           CREATE INDEX CONCURRENTLY ON dcim_interface (module_id)
           WHERE device_id IS NULL;
           CREATE INDEX CONCURRENTLY ON dcim_modulebay (parent_module_id)
           WHERE parent_device_id IS NULL;
         Drop them after the migration completes if not needed ongoing.
    """

    dependencies = [
        # TODO: replace with the real latest dcim migration in your branch, e.g.:
        # ("dcim", "0070_some_previous_migration"),
        ("dcim", "0090_cablepath_add_lane_fields"),
    ]

    operations = [
        migrations.RunPython(
            code=backpopulate_device,
            reverse_code=clear_backpopulated_device,
            hints={"target_db": "default"},
        ),
    ]
