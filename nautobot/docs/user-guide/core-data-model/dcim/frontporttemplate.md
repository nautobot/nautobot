# Front Port Templates

A template for a front-facing pass-through port that will be created on all instantiations of the parent device type. Front ports may have a physical type assigned, and must be associated with a corresponding rear port and position. This association will be automatically replicated when the device type is instantiated.

+++ 1.4.5
    The fields `created` and `last_updated` were added to all device component template models. If you upgraded from Nautobot 1.4.4 or earlier, the values for these fields will default to `None` (null).
