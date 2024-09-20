# Power Ports

A power port represents the inlet of a device where it draws its power, i.e. the connection port(s) on a device's power supply. Each power port may be assigned a physical type, as well as allocated and maximum draw values (in watts). These values can be used to calculate the overall utilization of an upstream power feed.

!!! info
    When creating a power port on a device which supplies power to downstream devices, the allocated and maximum draw numbers should be left blank. Utilization will be calculated by taking the sum of all power ports of devices connected downstream.

Cables can connect power ports only to power outlets or power feeds. (Pass-through ports cannot be used to model power distribution.)

+++ 1.4.5
    The fields `created` and `last_updated` were added to all device component models. If you upgraded from Nautobot 1.4.4 or earlier, the values for these fields will default to `None` (null).

+/- 2.3.0
    This model has been updated to support being installed in [Modules](module.md). As a result, there are now two fields for assignment to a Device or Module. One of the `device` or `module` fields must be populated but not both. If a `module` is supplied, the `device` field must be null, and similarly the `module` field must be null if a `device` is supplied.

## Example Power Topology

![Power distribution model](../../../media/power_distribution.png)
