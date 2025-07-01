# Power Feed

A power feed represents a electrical connection that distributes power from a [power panel](./powerpanel.md) to devices or to other power panels. Power feeds can be connected via cables to device power ports and may optionally be assigned to a rack for tracking power distribution.

Power feeds define the electrical characteristics of the circuit they represent and are categorized by both their operational type (type) and physical path (side) to enable accurate modeling of redundant power configurations.

## Type

The `type` field defines the operational type of the power feed in relation to other feeds that power the same equipment:

* **Primary**: The main power feed for a device or rack
* **Redundant**: A backup or secondary power feed

The interpretation of these types depends on the overall power design. For example, in an active-active (2N) configuration, a device might be served by two `Primary` feeds. In an active-passive (N+1) configuration, it would be served by one `Primary` and one `Redundant` feed.

## Side

The `side` field defines the physical path or source of the power feed. It represents which power distribution train the circuit originates from, which is crucial for modeling fault tolerance:

* **A-Side**: The power feed originates from the "A" power train
* **B-Side**: The power feed originates from the "B" power train  
* **C-Side**: For complex designs with a third redundant power train

If a power feed is part of a single, non-redundant power system (as in a Tier I or Tier II data center), the `side` field can be left blank.

## Status

Each power feed must be assigned an operational [`status`](../../platform-functionality/status.md). The following statuses are available by default:

* Offline
* Active
* Planned
* Failed

## Panel-to-Panel Distribution

Power feeds can connect one power panel to another by specifying a `destination_panel`. This enables modeling of hierarchical power distribution where power flows from upstream panels to downstream panels.

!!! note
    The `destination_panel` field should only be used for panel-to-panel connections in the power distribution hierarchy. When connecting a power feed to a rack-level PDU, leave `destination_panel` blank since rack PDUs should be modeled as [devices](./device.md) with [power outlets](./poweroutlet.md), not as power panels.

## Electrical Characteristics

Each power feed defines the electrical characteristics of the circuit:

* Supply type (AC or DC)
* Phase (single or three-phase)
* Voltage
* Amperage
* Maximum utilization (percentage)

## Breaker Configuration

Power feeds can specify their breaker configuration within the source power panel:

* **Breaker position**: The starting circuit position number in the panel
* **Breaker poles**: The number of poles the breaker occupies (1, 2, or 3)

When breaker positions are specified, Nautobot validates that the configuration fits within the panel's circuit capacity and prevents conflicts with other power feeds.

## Modeling Power Redundancy

By combining the `type` and `side` fields, you can model various industry-standard power redundancy configurations:

| Uptime Tier | Design | Feed 1 | Feed 2 |
| :--- | :--- | :--- | :--- |
| Tier I/II | Single Path (N) | `type=Primary`, `side=` (blank) | (none) |
| Tier III | Active/Passive (N+1) | `type=Primary`, `side=A-Side` | `type=Redundant`, `side=B-Side` |
| Tier IV | Active/Active (2N) | `type=Primary`, `side=A-Side` | `type=Primary`, `side=B-Side` |

!!! info
    Cables can connect power feeds only to device power ports. Pass-through ports cannot be used to model power distribution. The power utilization of a rack is calculated when one or more power feeds are assigned to the rack and connected to devices that draw power.

## Example Power Topology

![Power distribution model](../../../media/power_distribution.png){: style="width: 50%"}
