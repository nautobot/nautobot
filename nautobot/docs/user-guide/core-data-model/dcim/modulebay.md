# Module Bays

+++ 2.3.0

Module bays represent a space or slot within a parent [Device](device.md) or [Module](module.md) in which a module may be installed. Modules represent modular components within a device such as line cards, supervisor modules, network modules, or transceivers. For example, a modular switch may contain open slots for line cards, each of which is represented as a module bay. Each line card within the switch would be defined as a module installed in one of the module bays.

In addition to module bays within a device, module bays may also be defined within a module. For example, a line card may contain GBIC or SFP slots for installing transceivers. The GBIC or SFP slots would be represented as module bays within the line card module and the transceivers would be represented as modules containing one or more interfaces.

Module bays contain a required `position` field that is unique to the parent device or module. The position may be used when automatically populating the child components of a module, such as interface naming (`Ethernet1/<position>/1`).

Since module bays can be nested within modules, there are two fields on module bay, `parent_module` and `installed_module` to reduce confusion.
