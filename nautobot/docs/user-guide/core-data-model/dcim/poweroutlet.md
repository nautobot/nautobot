# Power Outlets

Power outlets represent the outlets on a power distribution unit (PDU) or other device that supply power to dependent devices. Each power port may be assigned a physical type, and may be associated with a specific feed leg (where three-phase power is used) and/or a specific upstream power port. This association can be used to model the distribution of power within a device.

For example, imagine a PDU with one power port which draws from a three-phase feed and 48 power outlets arranged into three banks of 16 outlets each. Outlets 1-16 would be associated with leg A on the port, and outlets 17-32 and 33-48 would be associated with legs B and C, respectively.

For rack per-phase power utilization, assign a `feed_leg` to each outlet supplying a downstream power port from a three-phase feed. This assignment determines which leg receives that port's allocated load. If a connected outlet has no `feed_leg`, the rack's per-phase graphs are hidden because the load cannot be attributed to a leg; the overall power utilization is still displayed. Unconnected outlets do not require a leg assignment for these graphs. See [Rack Power Utilization](rack.md#rack-power-utilization) for the other conditions required to display per-phase graphs.

Cables can connect power outlets only to downstream power ports. (Pass-through ports cannot be used to model power distribution.)

+/- 2.3.0
    This model has been updated to support being installed in [Modules](module.md). As a result, there are now two fields for assignment to a Device or Module. One of the `device` or `module` fields must be populated but not both. If a `module` is supplied, the `device` field must be null, and similarly the `module` field must be null if a `device` is supplied.

## Example Power Topology

![Power distribution model](../../../media/power_distribution.png){: style="width: 50%"}
