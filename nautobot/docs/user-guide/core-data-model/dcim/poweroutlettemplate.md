# Power Outlet Templates

A template for a power outlet that will be created on all instantiations of the parent device type. Each power outlet can be assigned a physical type, and its power source may be mapped to a specific feed leg and power port template. This association will be automatically replicated when the device type is instantiated.

+++ 1.4.5
    The fields `created` and `last_updated` were added to all device component template models. If you upgraded from Nautobot 1.4.4 or earlier, the values for these fields will default to `None` (null).
