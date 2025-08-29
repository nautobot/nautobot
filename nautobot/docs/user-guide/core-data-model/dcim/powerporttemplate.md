# Power Port Templates

A template for a power port that will be created on all instantiations of the parent device type or module type. Each power port can be assigned a physical type, as well as a maximum and allocated draw in watts.

+/- 2.3.0
    This model has been updated to support being installed in [Modules](module.md) through the [ModuleType](moduletype.md) model. As a result, there are now two fields for assignment to a DeviceType or ModuleType. One of the `device_type` or `module_type` fields must be populated but not both. If a `module_type` is supplied, the `device_type` field must be null, and similarly the `module_type` field must be null if a `device_type` is supplied.

+++ 2.4.15
    Power Port Templates include a `power_factor` field for converting between watts (W) and volt-amps (VA) in power calculations.

    The power factor represents the ratio of real power (watts) to apparent power (volt-amps) and defaults to 0.95, which is typical for modern server equipment. To find the power factor for your specific equipment, check:

    - **Power supply datasheets** - Look for 80 PLUS certification specifications
    - **Server management interfaces** - iDRAC, iLO, or IPMI may display PSU power factor settings  
    - **Equipment specifications** - Listed in the electrical characteristics section

    Typical power factor ranges:

    - **0.95-0.99**: Modern servers with 80 PLUS Platinum/Titanium certified PSUs
    - **0.9-0.95**: Standard servers with 80 PLUS Gold/Silver/Bronze certification
    - **0.5-0.9**: Older equipment or basic power supplies without certification

    The power factor is used in rack power utilization calculations to accurately convert watts to volt-amps for proper capacity planning. For more information, see the [80 PLUS certification program](https://www.clearesult.com/80plus/).
