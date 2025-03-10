# Modules

+++ 2.3.0

A module is a physical component that can be installed in a device or another module, such as a line card in a switch or a GBIC or SFP slot in a line card. Modules are installed in [Module Bays](modulebay.md) and may contain device components such as interfaces, console ports, or power ports.

Modules must reference a [Module Type](moduletype.md) which defines the module's available components and their properties, similar to devices and device types. Modules inherit the `position` value from the module bay that they are installed in and this value may be used when automatically populating the child components of a module, such as interface naming (`Ethernet1/<position>/1`).

Similar to devices, modules created from a module type that has component templates defined will be automatically populated with the components.

Modules may have a `serial` or `asset_tag` defined for tracking purposes.

Since modules may be installed within a module bay and also contain module bays themselves, there is a field called `parent_module_bay` to reference the module bay that the module is installed in and a field called `module_bays` to reference any module bays contained within the module.

In order to support modules that may exist as spares in inventory and not installed in a device, the `location` field may be populated instead of `parent_module_bay`. However both fields may not be populated simultaneously. A `location` may only be set on a module if it is not installed in a module bay. If a `parent_module_bay` is supplied, the location of the module will be inherited from the parent module bay.

When installing a module into a module bay, the module type must match the module bay's [module family](modulefamily.md), if it is assigned to one.
