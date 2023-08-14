# Inventory Items

Inventory items represent hardware components installed within a device, such as a power supply or CPU or line card. Inventory items are distinct from other device components in that they cannot be templatized on a device type, and cannot be connected by cables. They are intended to be used primarily for inventory purposes.

Each inventory item can be assigned a manufacturer, part ID, serial number, and asset tag (all optional). A boolean toggle is also provided to indicate whether each item was entered manually or discovered automatically (by some process outside of Nautobot).

Inventory items are hierarchical in nature, such that any individual item may be designated as the parent for other items. For example, an inventory item might be created to represent a line card which houses several SFP optics, each of which exists as a child item within the device.

+++ 1.4.5
    The fields `created` and `last_updated` were added to all device component models. If you upgraded from Nautobot 1.4.4 or earlier, the values for these fields will default to `None` (null).
