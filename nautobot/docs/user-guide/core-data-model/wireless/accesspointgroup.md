# Access Point Groups

AccessPointGroup represents a set of wireless devices sharing the same wireless configuration. Group broadcasts the same [Wireless Networks](wirelessnetwork.md) with the same [Radio Profiles](radiopofiles.md).

The AccessPointGroup is enforced, even if you intend to only have a single access point device. This is done in the interest of simplicity, and should be explicitly documented.

Fields on the Access Point Group include:

- Name
- [Devices](../dcim/device.md)
- [Wireless Networks](wirelessnetwork.md)
- [Radio Profiles](radioprofile.md)
- [Controller](../dcim/controller.md)

## Controller Managed Access Point Groups

Controllers can manage many Access Point Groups. The wireless devices that are managed by a Controller will show up on the Wireless Devices tab, but not on the Controller Managed Device Group. This is done to allow the flexibility of Access Point Groups to be Standalone or Centrally managed. A Device can still be associated to both a Controller Managed Device Group and an Access Point Group.
