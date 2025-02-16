# Inventory Items

Inventory items represent hardware components installed within a device that cannot be modeled as either a [Module](module.md) or other device component. Inventory items are distinct from other device components in that they cannot be templatized on a device type, and cannot be connected by cables. They are intended to be used primarily for inventory purposes.

Each inventory item can be assigned a manufacturer, part ID, serial number, and asset tag (all optional). A boolean toggle is also provided to indicate whether each item was entered manually or discovered automatically (by some process outside of Nautobot).

Inventory items are hierarchical in nature, such that any individual item may be designated as the parent for other items. Previously, it was recommended that line cards and similarly non-autonomous hardware should be modeled as inventory items within a device, but as of version 2.3.0 the [Module](module.md) model should be used instead.

!!! warning
    Unless a specific use case is identified for inventory items, they are likely to be completely replaced by [Modules](module.md) and removed in a future release of Nautobot.


+++ 2.2.0
    The [Software Version](softwareversion.md) model has been introduced to represent the software version that is currently installed on an inventory item. An optional software version field has been added to inventory items.
