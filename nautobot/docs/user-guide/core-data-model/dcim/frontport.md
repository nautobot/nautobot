# Front Ports

Front ports are pass-through ports used to represent physical cable connections that comprise part of a longer path. For example, the ports on the front face of a UTP patch panel would be modeled in Nautobot as front ports. Each port is assigned a physical type, and must be mapped to a specific rear port on the same device. A single front port may be mapped to multiple rear ports, using numeric positions to annotate the specific alignment of each.

+/- 2.3.0
    This model has been updated to support being installed in [Modules](module.md). As a result, there are now two fields for assignment to a Device or Module. One of the `device` or `module` fields must be populated but not both. If a `module` is supplied, the `device` field must be null, and similarly the `module` field must be null if a `device` is supplied.
