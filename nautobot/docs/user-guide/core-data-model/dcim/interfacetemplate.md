# Interface Templates

A template for a network interface that will be created on all instantiations of the parent device type or module type. Each interface may be assigned a physical or virtual type, and may be designated as "management-only."

+/- 2.3.0
    This model has been updated to support being installed in [Modules](module.md) through the [ModuleType](moduletype.md) model. As a result, there are now two fields for assignment to a DeviceType or ModuleType. One of the `device_type` or `module_type` fields must be populated but not both. If a `module_type` is supplied, the `device_type` field must be null, and similarly the `module_type` field must be null if a `device_type` is supplied.

+++ 2.4.22
    * `speed` (optional): Operational speed in Kbps as an integer. Value is rendered in the UI using human-readable units (e.g., Mbps/Gbps/Tbps).
    * `duplex` (optional): Duplex setting for copper twisted‑pair interfaces. Accepted values are `auto`, `full`, or `half`.

+++ 3.0.0
    Interfaces now have an optional `port_type` field which describes the physical connector. It is only applicable to physical interfaces; virtual and wireless interface types (including LAGs) cannot have a `port_type` set and attempting to do so will result in a validation error.
