# Power Feed

A power feed represents a electrical connection that distributes power from a [power panel](./powerpanel.md) to devices or to other power panels. Power feeds can be connected via cables to device power ports and may optionally be assigned to a rack for tracking power distribution.

Power feeds define the electrical characteristics of the circuit they represent and are categorized by both their operational type (type) and physical path (side) to enable accurate modeling of redundant power configurations.

## Type

The `type` field defines the operational type of the power feed in relation to other feeds that power the same equipment:

* **Primary**: The main power feed for a device or rack
* **Redundant**: A backup or secondary power feed

The interpretation of these types depends on the overall power design. For example, in an active-active (2N) configuration, a device might be served by two `Primary` feeds. In an active-passive (N+1) configuration, it would be served by one `Primary` and one `Redundant` feed.

## Power Path

+++ 2.4.15
    The `power_path` field defines the physical path or source of the power feed. It represents which power distribution path the circuit originates from, which is crucial for modeling fault tolerance:

* **Path A**: The power feed originates from the "A" power path
* **Path B**: The power feed originates from the "B" power path  

If a power feed is part of a single, non-redundant power system (as in a Tier I or Tier II data center), the `power_path` field can be left blank.

## Status

Each power feed must be assigned an operational [`status`](../../platform-functionality/status.md). The following statuses are available by default:

* Offline
* Active
* Planned
* Failed

## Panel-to-Panel Distribution

+++ 2.4.15
    Power feeds can connect one power panel to another by specifying a `destination_panel`. This enables modeling of hierarchical power distribution where power flows from upstream panels to downstream panels.

!!! note
    The `destination_panel` field should only be used for panel-to-panel connections in the power distribution hierarchy. When connecting a power feed to a rack-level PDU, leave `destination_panel` blank since rack PDUs should be modeled as [devices](./device.md) with [power outlets](./poweroutlet.md), not as power panels.

!!! warning "Cable Connection Exclusivity"
    A power feed cannot specify both a `destination_panel` and be connected via cable to another endpoint simultaneously. Power feeds can either:

    - Connect to a destination panel (panel-to-panel distribution), OR
    - Be cabled to a device power port or other endpoint

    But not both. This mutual exclusivity is enforced during validation to maintain data integrity.

## Electrical Characteristics

Each power feed defines the electrical characteristics of the circuit:

* Supply type (AC or DC)
* Phase (single or three-phase)
* Voltage
* Amperage
* Maximum utilization (percentage)

## Breaker Configuration

+++ 2.4.15
    Power feeds can specify their breaker configuration within the source power panel:

* **Breaker position**: The starting circuit position number in the panel
* **Breaker pole count**: The number of poles the breaker occupies (1, 2, or 3)

When breaker positions are specified, Nautobot validates that:

1. **Panel capacity**: The breaker configuration fits within the panel's circuit capacity
2. **Position conflicts**: No conflicts exist with other power feeds' breaker positions
3. **Auto-defaulting**: If a breaker position is specified without a pole count, it defaults to a single-pole breaker

The system calculates occupied positions based on standard electrical panel layouts where multi-pole breakers occupy consecutive positions with specific spacing requirements.

### Phase Designation

When breaker positions are configured, Nautobot automatically calculates the phase designation based on the occupied circuit positions. This follows standard electrical panel layouts where:

* Positions 1,2 = Phase A
* Positions 3,4 = Phase B  
* Positions 5,6 = Phase C
* Pattern repeats every 6 positions

The calculated phase designation can be:

* **Single-phase (1-pole)**: "A", "B", or "C" for single-pole breakers
* **Single-phase (2-pole)**: "A-B", "B-C", etc. for two-pole breakers (e.g., 240V split-phase)
* **Three-phase (3-pole)**: "A-B-C" for three-pole breakers

This information is available through the `phase_designation` property and helps with load balancing and electrical planning.

### Position Tracking

The `occupied_positions` property provides a comma-separated string of all circuit positions occupied by the power feed. This is useful for understanding panel utilization and avoiding conflicts when adding new feeds.

## Modeling Power Redundancy

By combining the `type` and `power_path` fields, you can model various industry-standard power redundancy configurations:

| Uptime Tier | Design | Feed 1 | Feed 2 |
| :--- | :--- | :--- | :--- |
| Tier I/II | Single Path (N) | `type=Primary`, `power_path=` (blank) | (none) |
| Tier III | Active/Passive (N+1) | `type=Primary`, `power_path=a` | `type=Redundant`, `power_path=b` |
| Tier IV | Active/Active (2N) | `type=Primary`, `power_path=a` | `type=Primary`, `power_path=b` |

!!! info
    Cables can connect power feeds only to device power ports. Pass-through ports cannot be used to model power distribution. The power utilization of a rack is calculated when one or more power feeds are assigned to the rack and connected to devices that draw power.

## Example Power Topology

![Power distribution model](../../../media/power_distribution.png){: style="width: 50%"}
