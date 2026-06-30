# Cable Types

+++ 3.2

While the definition and usage of cable types is optional when modeling simple point-to-point [cables](cable.md), cable types are primarily required when modeling [breakout cables](../../feature-guides/breakout-cables.md) in Nautobot. A cable type defines the physical connectivity of cables using this type, including the number of connectors at each side, the number of internal lanes within the the cable, and the mapping between connectors and lanes.

## Fields

A cable type has the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique name for the cable type |
| `a_connectors` | integer | Yes | Number of physical connectors on the "A" side of the cable |
| `b_connectors` | integer | Yes | Number of physical connectors on the "B" side of the cable |
| `total_lanes` | integer | Yes | Total number of logical lanes within the cable |
| `mapping` | JSON | Yes | Array of `total_lanes` entries describing the relations among `a_connectors` `b_connectors`, and individual lanes within the cable |
| `description` | string | No | Descriptive details |
| `manufacturer` | [Manufacturer](manufacturer.md) | No | Manufacturer information |
| `part_number` | string | No | Part number |
| `has_embedded_transceivers` | Boolean | No | Informational - whether transceivers such as SFPs are built in to the cable |
| `is_shuffle` | Boolean | No | Informational - whether the lane mapping is non-linear, polarity-shuffled, etc. |
| `strands_per_lane` | integer | No | Informational - number of physical strands per logical lane |
| `polarity_method` | string | No | Informational - fiber polarity method |

### Validation

* If a cable type has differing `a_connectors` and `b_connectors` values, the A side must represent the "trunk" end of the cable (in other words, `a_connectors <= b_connectors` is enforced). This is to avoid inadvertent definition of redundant symmetric cable types (such as both a "1x4 breakout" and a "4x1 breakout").
* The `total_lanes` must be evenly divisible by both `a_connectors` and `b_connectors`.
* The `mapping` must contain exactly `total_lanes` entries, each of which has a valid and unique set of `a_connector`, `a_position`, `b_connector`, and `b_position` values (as well as an optional `label` value). Refer to the [Breakout Cables feature guide](../../feature-guides/breakout-cables.md) for examples of valid mappings.
* An existing cable type that is referenced by existing cables may not change its `a_connectors`, `b_connectors`, `total_lanes`, `strands_per_lane`, or `mapping` values as doing so would invalidate those cables.
* An existing cable type that is referenced by existing cables may not be deleted.

## Properties

| Property | Type | Description |
|----------|------|-------------|
| `a_positions` | integer | Number of lane positions per "A" side connector (`total_lanes / a_connectors`) |
| `b_positions` | integer | Number of lane positions per "B" side connector (`total_lanes / b_connectors`) |
| `total_strands` | integer | Number of physical strands within the cable (`total_lanes x strands_per_lane`) |
| `is_breakout` | Boolean | Whether this is a breakout cable (`b_connectors > a_connectors`) |
| `is_multi_connector` | Boolean | Whether this is a multi-connector cable or a simple point-to-point one |
| `trunk_end` | string | `"A"` for breakout cables, None for non-breakout cables |
