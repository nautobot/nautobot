# Interface Templates

A template for a network interface that will be created on all instantiations of the parent device type. Each interface may be assigned a physical or virtual type, and may be designated as "management-only."

+++ 1.4.5
    The fields `created` and `last_updated` were added to all device component template models. If you upgraded from Nautobot 1.4.4 or earlier, the values for these fields will default to `None` (null).
