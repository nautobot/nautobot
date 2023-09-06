# Front Ports

Front ports are pass-through ports used to represent physical cable connections that comprise part of a longer path. For example, the ports on the front face of a UTP patch panel would be modeled in Nautobot as front ports. Each port is assigned a physical type, and must be mapped to a specific rear port on the same device. A single rear port may be mapped to multiple rear ports, using numeric positions to annotate the specific alignment of each.

+++ 1.4.5
    The fields `created` and `last_updated` were added to all device component models. If you upgraded from Nautobot 1.4.4 or earlier, the values for these fields will default to `None` (null).
