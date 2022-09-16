# Locations

+++ 1.4.0

To locate network information more precisely than a Site defines, you can define a hierarchy of Locations within each Site. Data objects such as devices, prefixes, VLAN groups, etc. can thus be mapped or assigned to a specific building, wing, floor, room, etc. as appropriate to your needs.

Once you have defined the hierarchy of Location Types that you wish to use, you can then define Locations. Any "top-level" Locations (those whose Location Type has no parent) belong directly to a Site, while "child" Locations belong to their immediate parent Location, rather than to the Site as a whole.

!!! info
    At present, Locations fill the conceptual space between the more abstract Region and Site models and the more concrete Rack Group model. In a future Nautobot release, some or all of these other models may be collapsed into Locations. That is to say, in the future you might not deal with Regions and Sites as distinct models, but instead your Location Type hierarchy might include these higher-level categories, becoming something like Country ← City ← Site ← Building ← Floor ← Room.

Much like Sites, each Location must be assigned a name and operational [`status`](../../models/extras/status.md). The same default operational statuses are defined for Locations as for Sites, but as always, you can customize these to suit your needs. Locations can also be assigned to a tenant.
