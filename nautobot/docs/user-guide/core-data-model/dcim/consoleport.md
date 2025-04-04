# Console Ports

A console port provides connectivity to the physical console of a device. These are typically used for temporary access by someone who is physically near the device, or for remote out-of-band access provided via a networked console server. Each console port may be assigned a physical type.

Cables can connect console ports to console server ports or pass-through ports.

+/- 2.3.0
    This model has been updated to support being installed in [Modules](module.md). As a result, there are now two fields for assignment to a Device or Module. One of the `device` or `module` fields must be populated but not both. If a `module` is supplied, the `device` field must be null, and similarly the `module` field must be null if a `device` is supplied.
