# Module Types

+++ 2.3.0

Module types represent a category of [Modules](module.md) that may be installed within a [Module Bay](modulebay.md). For example, you may want to create module types representing different types of line cards, supervisor modules, or transceivers. Each module type must be associated to a [Manufacturer](manufacturer.md) and a `model` unique to that manufacturer. Optionally, module types may define a part number, which may be useful for documenting the SKU used for ordering a module. Module types may contain templates for components that are common to all modules of that type, such as interfaces, power ports or module bays. Similar to devices and device types, when a module is created from a module type that has component templates defined, the module will be automatically populated with the components.
