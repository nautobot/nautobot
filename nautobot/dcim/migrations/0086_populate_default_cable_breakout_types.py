"""Populate default CableBreakoutType records for common cable configurations."""

from django.db import migrations

# AOC Ethernet Breakouts (strands_per_lane=1)
# Fiber MPO Fanouts (strands_per_lane=2, duplex)
TEMPLATES = {
    # ── AOC Ethernet Breakouts ──
    "1x2 AOC Fanout": {
        "description": "1 trunk connector broken out to 2 individual legs",
        "a_connectors": 1,
        "a_positions": 2,
        "b_connectors": 2,
        "b_positions": 1,
        "mapping": [
            {"a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1},
            {"a_connector": 1, "a_position": 2, "b_connector": 2, "b_position": 1},
        ],
        "strands_per_lane": 1,
        "polarity_method": "",
        "is_shuffle": False,
    },
    "1x4 AOC Fanout": {
        "description": "1 trunk connector broken out to 4 individual legs",
        "a_connectors": 1,
        "a_positions": 4,
        "b_connectors": 4,
        "b_positions": 1,
        "mapping": [{"a_connector": 1, "a_position": i, "b_connector": i, "b_position": 1} for i in range(1, 5)],
        "strands_per_lane": 1,
        "polarity_method": "",
        "is_shuffle": False,
    },
    "1x8 AOC Fanout": {
        "description": "1 trunk connector broken out to 8 individual legs",
        "a_connectors": 1,
        "a_positions": 8,
        "b_connectors": 8,
        "b_positions": 1,
        "mapping": [{"a_connector": 1, "a_position": i, "b_connector": i, "b_position": 1} for i in range(1, 9)],
        "strands_per_lane": 1,
        "polarity_method": "",
        "is_shuffle": False,
    },
    "2x4 AOC Fanout": {
        "description": "2 trunk connectors (4 lanes each) broken out to 8 individual legs",
        "a_connectors": 2,
        "a_positions": 4,
        "b_connectors": 8,
        "b_positions": 1,
        "mapping": [
            {"a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1},
            {"a_connector": 1, "a_position": 2, "b_connector": 2, "b_position": 1},
            {"a_connector": 1, "a_position": 3, "b_connector": 3, "b_position": 1},
            {"a_connector": 1, "a_position": 4, "b_connector": 4, "b_position": 1},
            {"a_connector": 2, "a_position": 1, "b_connector": 5, "b_position": 1},
            {"a_connector": 2, "a_position": 2, "b_connector": 6, "b_position": 1},
            {"a_connector": 2, "a_position": 3, "b_connector": 7, "b_position": 1},
            {"a_connector": 2, "a_position": 4, "b_connector": 8, "b_position": 1},
        ],
        "strands_per_lane": 1,
        "polarity_method": "",
        "is_shuffle": False,
    },
    # ── Fiber MPO Fanouts ──
    "MPO-8 → 4xLC Duplex": {
        "description": "MPO-8 trunk fanning out to 4 LC duplex connections",
        "a_connectors": 1,
        "a_positions": 4,
        "b_connectors": 4,
        "b_positions": 1,
        "mapping": [{"a_connector": 1, "a_position": i, "b_connector": i, "b_position": 1} for i in range(1, 5)],
        "strands_per_lane": 2,
        "polarity_method": "straight-through",
        "is_shuffle": False,
    },
    "MPO-12 → 6xLC Duplex": {
        "description": "MPO-12 trunk fanning out to 6 LC duplex connections",
        "a_connectors": 1,
        "a_positions": 6,
        "b_connectors": 6,
        "b_positions": 1,
        "mapping": [{"a_connector": 1, "a_position": i, "b_connector": i, "b_position": 1} for i in range(1, 7)],
        "strands_per_lane": 2,
        "polarity_method": "straight-through",
        "is_shuffle": False,
    },
    "MPO-24 → 12xLC Duplex": {
        "description": "MPO-24 trunk fanning out to 12 LC duplex connections",
        "a_connectors": 1,
        "a_positions": 12,
        "b_connectors": 12,
        "b_positions": 1,
        "mapping": [{"a_connector": 1, "a_position": i, "b_connector": i, "b_position": 1} for i in range(1, 13)],
        "strands_per_lane": 2,
        "polarity_method": "straight-through",
        "is_shuffle": False,
    },
    "MPO-24 → 2xMPO-12": {
        "description": "MPO-24 trunk split into 2 MPO-12 trunks (6 lanes each)",
        "a_connectors": 1,
        "a_positions": 12,
        "b_connectors": 2,
        "b_positions": 6,
        "mapping": [
            # A1 positions 1-6 → B1 positions 1-6
            *[{"a_connector": 1, "a_position": i, "b_connector": 1, "b_position": i} for i in range(1, 7)],
            # A1 positions 7-12 → B2 positions 1-6
            *[{"a_connector": 1, "a_position": i + 6, "b_connector": 2, "b_position": i} for i in range(1, 7)],
        ],
        "strands_per_lane": 2,
        "polarity_method": "straight-through",
        "is_shuffle": False,
    },
    "2xMPO-12 → 12xLC Duplex": {
        "description": "2 MPO-12 trunks (6 lanes each) fanning out to 12 LC duplex connections",
        "a_connectors": 2,
        "a_positions": 6,
        "b_connectors": 12,
        "b_positions": 1,
        "mapping": [
            # A1 positions 1-6 → B connectors 1-6
            *[{"a_connector": 1, "a_position": i, "b_connector": i, "b_position": 1} for i in range(1, 7)],
            # A2 positions 1-6 → B connectors 7-12
            *[{"a_connector": 2, "a_position": i, "b_connector": i + 6, "b_position": 1} for i in range(1, 7)],
        ],
        "strands_per_lane": 2,
        "polarity_method": "straight-through",
        "is_shuffle": False,
    },
}


def populate_breakout_templates(apps, schema_editor):
    """Create default breakout template configurations."""
    CableBreakoutType = apps.get_model("dcim", "CableBreakoutType")
    for name, defaults in TEMPLATES.items():
        CableBreakoutType.objects.get_or_create(name=name, defaults=defaults)


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0085_cablebreakouttype"),
    ]

    operations = [
        migrations.RunPython(populate_breakout_templates, migrations.RunPython.noop),
    ]
