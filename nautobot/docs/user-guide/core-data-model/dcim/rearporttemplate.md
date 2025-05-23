# Rear Port Templates

A template for a rear-facing pass-through port that will be created on all instantiations of the parent device type or module type. Each rear port may have a physical type and one or more front port templates assigned to it. The number of positions associated with a rear port determines how many front ports can be assigned to it (the maximum is 1024).

+/- 2.3.0
    This model has been updated to support being installed in [Modules](module.md) through the [ModuleType](moduletype.md) model. As a result, there are now two fields for assignment to a DeviceType or ModuleType. One of the `device_type` or `module_type` fields must be populated but not both. If a `module_type` is supplied, the `device_type` field must be null, and similarly the `module_type` field must be null if a `device_type` is supplied.
