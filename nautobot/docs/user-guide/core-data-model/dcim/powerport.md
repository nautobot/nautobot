# Power Ports

A power port represents the inlet of a device where it draws its power, i.e. the connection port(s) on a device's power supply. Each power port may be assigned a physical type, as well as allocated and maximum draw values (in watts). These values can be used to calculate the overall utilization of an upstream power feed.

!!! info
    When creating a power port on a device which supplies power to downstream devices, the allocated and maximum draw numbers should be left blank. Utilization will be calculated by taking the sum of all power ports of devices connected downstream.

Cables can connect power ports only to power outlets or power feeds. (Pass-through ports cannot be used to model power distribution.)

+/- 2.3.0
    This model has been updated to support being installed in [Modules](module.md). As a result, there are now two fields for assignment to a Device or Module. One of the `device` or `module` fields must be populated but not both. If a `module` is supplied, the `device` field must be null, and similarly the `module` field must be null if a `device` is supplied.

+++ 2.4.15
    Power Ports include a `power_factor` field for converting between watts (W) and volt-amps (VA) in power calculations.

    The power factor represents the ratio of real power (watts) to apparent power (volt-amps) and defaults to 0.95, which is typical for modern server equipment. To find the power factor for your specific equipment, check:

    - **Power supply datasheets** - Look for 80 PLUS certification specifications
    - **Server management interfaces** - iDRAC, iLO, or IPMI may display PSU power factor settings  
    - **Equipment specifications** - Listed in the electrical characteristics section

    Typical power factor ranges:

    - **0.95-0.99**: Modern servers with 80 PLUS Platinum/Titanium certified PSUs
    - **0.9-0.95**: Standard servers with 80 PLUS Gold/Silver/Bronze certification
    - **0.5-0.9**: Older equipment or basic power supplies without certification

    The power factor is used in rack power utilization calculations to accurately convert watts to volt-amps for proper capacity planning. For more information, see the [80 PLUS certification program](https://www.clearesult.com/80plus/).

## Example Power Topology

![Power distribution model](../../../media/power_distribution.png){: style="width: 50%"}
