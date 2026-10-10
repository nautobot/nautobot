# Module Types

+++ 2.3.0

Module types represent a category of [Modules](module.md) that may be installed within a [Module Bay](modulebay.md). For example, you may want to create module types representing different types of line cards, supervisor modules, or transceivers. Each module type must be associated to a [Manufacturer](manufacturer.md) and a `model` unique to that manufacturer. Optionally, module types may define a part number, which may be useful for documenting the SKU used for ordering a module. Module types may contain templates for components that are common to all modules of that type, such as interfaces, power ports or module bays. Similar to devices and device types, when a module is created from a module type that has component templates defined, the module will be automatically populated with the components.

A module type can also record the physical weight of the module, stored together with its unit: kilograms, grams, pounds or ounces. A unit must be selected whenever a weight is set.

+++ 3.3.0
    The optional `weight`/`weight_unit` fields have been added. They are also included when importing or exporting a single module type in the [devicetype-library](https://github.com/nautobot/devicetype-library) YAML or JSON format.
