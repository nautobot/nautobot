# Breakout Cables

+++ 3.2

Breakout cables are multi-lane cable assemblies where a single physical cable splits into multiple individual connections. Common examples include:

- A **400G QSFP-DD** port broken out into **4×100G SFP** lanes, each connecting to a different leaf switch
- A **40GE** interface broken out into **4×10GE** lanes terminating on four separate server NICs
- An **MPO-12** trunk fanning out to **twelve individual LC duplex** connections at a fiber distribution frame
- Two **MPO-8** trunks (4 lanes each) fanning out to **8 individual legs** across multiple devices

In Nautobot, a breakout cable is simply a [cable](../core-data-model/dcim/cable.md) with a breakout [cable type](../core-data-model/dcim/cabletype.md) assigned. Standard cables and breakout cables appear in the same cable list - the breakout behavior is unlocked by the assigned cable type.

## Terminology

These terms describe the physical parts of a breakout cable and how they relate to each other in Nautobot.

### Naming Convention

Throughout Nautobot, a specific endpoint on a cable is referenced as **`{Side}{Connector}`** -- for example, `A1` or `B3`. The side is a single letter (`A` or `B`), and the connector is a 1-based number. Position (the lane within a connector) is internal detail and not shown in the primary label -- it appears in tooltips or expanded views when relevant.

### Connector

A **connector** is a physical plug or receptacle at one end of a cable. A standard point-to-point cable has one connector on each end. A breakout cable may have a different number of connectors on each end -- for example, one MPO connector on the trunk side and four LC connectors on the leg side.

The number of connectors on each side of a cable in Nautobot is defined by its selected cable type, if any. (A simple point-to-point cable with no specified cable type implicitly has one connector on each side.) As a matter of self-consistency, Nautobot enforces that breakout cable types designate the "A" side as the trunk (fewer connectors) and the "B" side as the breakout legs (more connectors).

### Position

A **position** is a single path within a connector. A connector may carry one or more positions. Each position represents one logical channel through that connector.

- A simple SFP connector has **1 position** -- one path in, one path out.
- A QSFP connector has **4 positions** -- four parallel paths.
- An MPO-12 connector used for duplex fiber has **6 positions** (12 strands ÷ 2 strands per lane).

In the cable type definition, the total number of lanes, A side connectors, and B side connectors is defined, and the `a_positions` and `b_positions` properties are derived from the `total_lanes ÷ a_connectors` and `total_lanes ÷ b_connectors`. All connectors on the same side of a cable are assumed to have the same number of positions; varying the number of positions per individual connector on a side is not permitted.

For example, a 1x4 DAC breakout cable type would have 4 `total_lanes` and include 1 QSFP-DD connector (`a_connectors = 1` and therefore 4 positions, `a_positions = 4`) on Side A, and 4 SFP28 connectors (`b_connectors = 4` and therefore 1 position each, `b_positions = 1`) on Side B.

### Lane

A **lane** is one discrete end-to-end path through the entire cable, from an A-side connector+position to a B-side connector+position. The cable type's `mapping` field defines each lane thus: which A-side connector and position maps to which B-side connector and position, plus an optional label for each lane.

For a 1×4 breakout cable, there are 4 lanes in the mapping:

| Lane | A-Side | B-Side |
|------|--------|--------|
| 1 | Connector 1, Position 1 | Connector 1, Position 1 |
| 2 | Connector 1, Position 2 | Connector 2, Position 1 |
| 3 | Connector 1, Position 3 | Connector 3, Position 1 |
| 4 | Connector 1, Position 4 | Connector 4, Position 1 |

The total lane count equals the length of the mapping array: `a_connectors × a_positions` (which must equal `b_connectors × b_positions`).

### Strand

A **strand** is a single physical fiber or conductor within a cable. A lane may require one or more strands depending on the transmission technology:

| Technology | Strands Per Lane | Example |
|------------|-----------------|---------|
| Copper / DAC | 1 | One copper pair per lane |
| Duplex fiber (standard) | 2 | One strand transmits, one receives (Tx/Rx) |
| Parallel optics (PSM4, SR4) | 8 | Multiple strands per lane for higher bandwidth |

The `strands_per_lane` field on the cable type captures this. The total physical strand count is `total_lanes × strands_per_lane`. This is useful for fiber plant documentation and capacity planning -- for example, an MPO-12 cable with 6 duplex lanes has 12 total strands.

### Polarity

**Polarity** describes how the transmit (Tx) and receive (Rx) strands are arranged between the two ends of a fiber cable. Correct polarity ensures that the Tx output at one end connects to the Rx input at the other end. There are several standard polarity methods:

#### Straight-through (Method A / TIA-568)

Strand 1 at end A connects to strand 1 at end B. Strand 2 at A connects to strand 2 at B, and so on. The Tx/Rx swap happens at the connector -- one end uses a "key up" orientation and the other uses "key down," which provides the crossover.

This is the most common method for MPO trunk cables. It requires that one end of the cable has the connector installed in the opposite orientation (key up to key down).

#### Reversed (Method B)

Strand 1 at end A connects to strand N at end B (where N is the total strand count). Strand 2 at A connects to strand N-1 at B, and so on. Both connectors are "key up to key up." The cable itself provides the Tx/Rx swap by reversing the entire fiber order.

This is simple to understand and widely used. For a 12-strand MPO, strand 1 maps to strand 12, strand 2 to strand 11, etc.

#### Pair-reversed (Method C)

Strands are swapped in adjacent pairs rather than fully reversed. Strand 1 connects to strand 2, strand 2 to strand 1, strand 3 to strand 4, strand 4 to strand 3, and so on. Each Tx/Rx pair is locally swapped.

This is less common but used in specific high-density applications where pair-level polarity management is needed.

#### Other

Any non-standard polarity arrangement that doesn't fit the above methods. The actual strand mapping is defined by the lane mapping in the breakout template; the polarity method field is informational only and does not affect tracing or validation.

!!! note
    The `polarity_method` field is informational -- Nautobot does not validate or enforce strand-level polarity. It is intended for documentation and compliance purposes. The lane-level mapping (connector+position to connector+position) is what Nautobot uses for path tracing.

## Creating a Breakout Cable Type

Navigate to **Devices > Connections > Cable Types** and click **Add Cable Type**.

### General Information

Describe the cable type:

- **Name** - must be unique
- **Description** - optional
- **Manufacturer** - optional, if you want to treat cables from different vendors as distinct cable types
- **Part number** - optional, if you want to track the specific part number for a given cable type

### Connector and Lane Counts

Define the physical structure of the cable:

- **A connectors** - number of physical connectors on the A side (e.g., 1 for a single trunk port)
- **B connectors** - number of physical connectors on the B side (e.g., 4 for four individual legs)
- **Total lanes** - number of lanes within the cable, must be a multiple of both connector counts (e.g., 4 for a basic 1x4 breakout cable type)
- **Strands Per Lane** - number of physical strands per logical lane, informational only (1 for copper/DAC, 2 for duplex fiber, 8 for parallel optics)

### Fiber-Specific Fields

For fiber optic cable types, with more than one strand per lane:

- **Polarity Method** - the fiber polarity method (Straight-through, Reversed, Pair-reversed, Other). Informational only.

### Lane Mapping

The mapping defines how each lane connects the A-side and B-side connectors. By default, after you enter a valid combination of values for the "A connectors", "B connectors", and "Total lanes", Nautobot will auto-generate a likely mapping for you. This will likely suffice for most real-world breakout cables, but should you need to override it for a specific cable type, the create/edit form presents the mapping in two modes:

- **Table editor** - a table of form fields with one row per lane, allowing you to visually customize individual position assignments and/or lane labels. Use this for polarity shuffles or non-standard mappings.
- **JSON editor** - click the "JSON" button to switch to a raw JSON representation of the mapping. You can use this for advanced editing or pasting data from external sources.

#### Mapping JSON Format

Each entry in the mapping array maps one A-side connector+position pair to one B-side connector+position pair:

```json
[
  { "a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1, "label": "1" },
  { "a_connector": 1, "a_position": 2, "b_connector": 2, "b_position": 1, "label": "2" },
  { "a_connector": 1, "a_position": 3, "b_connector": 3, "b_position": 1, "label": "3" },
  { "a_connector": 1, "a_position": 4, "b_connector": 4, "b_position": 1, "label": "4" }
]
```

This example represents a 1×4 breakout: one 4-position A-side connector fans out to four single-position B-side connectors.

### Cable Type Lane Mapping Diagram

After successfully creating a cable type, its detail view in Nautobot shows an SVG diagram of the connector/position/lane mapping. A-side connectors appear on the left, B-side on the right, with lines representing the lanes joining the connectors. Connectors with multiple positions show the lane count in parentheses.

## Assigning a Cable Type to a Cable

Edit any cable and select a cable type from the **Cable Type** dropdown. (Note that this is different from the **Type** dropdown, which predates Nautobot v3.2.) Note that breakout cable types are not selectable if the cable is connected to non-compatible termination types (power and console cables cannot be breakout cables), but if you have defined a non-breakout cable type, you can use it even for such terminations.

When a cable type is assigned, the cable edit form dynamically updates to show the correct number of connector rows for each side. If the cable already had terminations (a standard A↔B connection), those terminations are preserved as the first connector on each side.

!!! tip
    Because a breakout cable always designates the "A" side of the cable as the trunk side, when updating an existing point-to-point cable to use a breakout cable type, you may find that the existing terminations of the table are initially on the "wrong" sides. There is a helpful "Swap A/B" button in the form that you can click to easily remedy this.

### Editing Connections

On the cable edit form, each connector row has three fields:

1. **Type** - select the termination type (Interface, Front Port, Rear Port, etc.)
2. **Parent** - select the parent object (Device, Circuit, etc.), filtered by type
3. **Termination** - select the specific termination object, filtered by parent

Changing the type dynamically swaps the parent and termination picker fields. Mixed termination types are supported, within logical limits -- for example, some lanes can connect to device interfaces while others connect to circuit terminations; however it would not make sense to mix interfaces and power outlets on the same cable.

## Understanding Cable Connections

### Cable Connections Table

The cable detail view shows a **Connections** table with Side A on the left and Side B on the right. Each connection shows:

- A **type icon** indicating the termination type (interface, front port, circuit termination, etc.)
- The **parent object** (device, circuit, or power panel) as a clickable link
- The **termination object** as a clickable link
- An **"Unconnected"** badge for lanes without a termination

### Cable Lane Mapping Diagram

Below the connections table, the cable detail view shows much the same information, this time as an SVG lane mapping diagram:

- **Green nodes** - connectors with a termination assigned
- **Gray nodes** - unconnected connectors
- **Lines** - show the mapping between A-side and B-side connectors

## Cable Path Tracing

When tracing a cable path that passes through a breakout cable, Nautobot follows the correct lane(s) via the cable type's mapping:

1. The trace identifies which connector and position the entry point is on
2. It looks up the mapped connector and position on the far side
3. If the far side is connected, the trace continues from that termination
4. If the far side is unconnected, the trace halts

## REST API

### Creating a Breakout Cable

```json
POST /api/dcim/cables/
{
    "cable_type": "<cable-type-uuid>",
    "label": "SRV1-SPINE1-BKO",
    "status": "<status-uuid>",
    "terminations": {
        "a": {
            "1": {
                "object_type": "dcim.interface",
                "id": "<interface-uuid>"
            }
        },
        "b": {
            "1": {
                "object_type": "dcim.interface",
                "id": "<interface-uuid>"
            },
            "2": {
                "object_type": "dcim.frontport",
                "id": "<front-port-uuid>"
            },
            "3": {
                "object_type": "circuits.circuittermination",
                "id": "<circuit-termination-uuid>"
            },
            "4": null
        }
    }
}
```

Note that the fourth B-side termination is null, representing an unconnected leg.

### Reading Cable Terminations

In API responses, the cable's `terminations` field is rendered in the same `{"a": {...}, "b": {...}}` shape, keyed by side and then by 1-indexed connector number. Each slot value is a brief representation of the termination (or the full nested serializer when `?depth=1` or greater is requested), and uncabled connectors on a breakout cable appear as explicit `null` slots.

The legacy `termination_a` / `termination_b` (and `termination_a_type` / `termination_a_id`, etc.) fields remain on the cable serializer for backward compatibility, and refer to connector 1 on each side.

!!! note
    The nested `terminations` field cannot be flattened into CSV, so it is omitted from CSV exports of cables. To export per-connector termination rows as CSV, use the [Cable to Cable Termination](../core-data-model/dcim/cabletocabletermination.md) endpoint instead, e.g. `/api/dcim/cables-to-cable-terminations/?cable=<cable-uuid>&format=csv`.

### Filtering

- `?cable_type=<uuid>` - cables using a specific cable type
- `?has_cable_type=false` - standard cables only
- `?termination_a_type=dcim.interface` - cables with A-side interfaces
- `?termination_b_type=dcim.interface` - cables with B-side interfaces
- `?termination_type=dcim.interface` - cables with an interface on A and/or B side
- `?is_disconnected=true` - cables with at least one disconnected connector

## Demo Data

A management command generates comprehensive demo data for testing and demonstration purposes:

```bash
nautobot-server create_breakout_demo_data
```

Use `--flush` to delete and recreate:

```bash
nautobot-server create_breakout_demo_data --flush
```

This creates:

- 9 breakout templates (1×4, 40G→4×10G, MPO-12, 2×4 shuffle, 1×2, mixed-type, 2×4→8×1 fanout, 4×1→1×4 aggregation, 8×1→2×4 reverse)
- 15+ cables covering all termination types (interface, front port, rear port, circuit termination, power, console)
- Spare interfaces on all devices for testing
- All contained in a single "DEMO-DC1" location
