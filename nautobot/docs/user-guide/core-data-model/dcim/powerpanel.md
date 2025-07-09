# Power Panel

A power panel represents a distribution point in Nautobot's electrical power hierarchy, distributing power through one or more power feeds. Power panels can receive power from upstream sources and distribute it downstream through power feeds. In a data center environment, power panels are typically arranged in hierarchical distributions - from utility connections through main distribution panels, UPS systems, switchgear, and down to individual racks.

Each power panel must be assigned to a location, and may optionally be assigned to a rack group.

!!! info
    Rack-level PDUs should **not** be modeled as power panels. Instead, they should be modeled as devices with [power outlets](./poweroutlet.md) that connect to power feeds from upstream power panels.

## Panel Types

Power panels can be categorized by type to better represent different components in the power distribution hierarchy:

* **Utility** - Main utility connection point
* **Generator** - Emergency power generation equipment
* **Switchgear** - High-voltage switching and protection equipment
* **Main Distribution Panel (MDP)** - Primary distribution point for incoming power
* **Uninterruptible Power Supply (UPS)** - Battery backup power systems
* **Transfer Switch** - Automatic or manual switching between power sources
* **Power Distribution Unit (PDU)** - Facility-level power distribution equipment (not rack-level PDUs)
* **Panelboard** - Standard electrical distribution panel
* **Mini Load Center (MLC)** - Smaller distribution panels
* **Remote Power Panel (RPP)** - Distributed power panels in remote locations

## Circuit Positions

Power panels can optionally specify the total number of circuit positions available. This helps track breaker capacity and prevents overallocation when power feeds specify breaker positions. For example, a 42-position panelboard would have `circuit_positions` set to 42.

## Panel-to-Panel Distribution

Power panels can distribute power to other power panels through power feeds with a specified `destination_panel`. This enables modeling of hierarchical power distribution where power flows from upstream panels (like utility switchgear or MDPs) to downstream panels (like UPS systems or panelboards). This allows Nautobot to model complete power paths from utility sources through multiple distribution tiers down to rack-level devices.

!!! note
    Power panels model hierarchical power distribution relationships through panel-to-panel connections. While some panels may serve as root sources (like utility connections), others function as intermediate distribution points receiving power from upstream panels and distributing it downstream.

## Example Power Topology

![Power distribution model](../../../media/power_distribution.png){: style="width: 50%"}
