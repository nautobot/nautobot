# Interface Templates

A template for a network interface that will be created on all instantiations of the parent device type or module type. Each interface may be assigned a physical or virtual type, and may be designated as "management-only."

+++ 1.4.5
    The fields `created` and `last_updated` were added to all device component template models. If you upgraded from Nautobot 1.4.4 or earlier, the values for these fields will default to `None` (null).

+/- 2.3.0
    This model has been updated to support being installed in [Modules](module.md) through the [ModuleType](moduletype.md) model. As a result, there are now two fields for assignment to a DeviceType or ModuleType. One of the `device_type` or `module_type` fields must be populated but not both. If a `module_type` is supplied, the `device_type` field must be null, and similarly the `module_type` field must be null if a `device_type` is supplied.
