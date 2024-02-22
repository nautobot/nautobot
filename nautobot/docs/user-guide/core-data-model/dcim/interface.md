# Interfaces

Interfaces in Nautobot represent network interfaces used to exchange data with connected devices. On modern networks, these are most commonly Ethernet, but other types are supported as well. Each interface must be assigned a type, an operational [`status`](../../platform-functionality/status.md) and may optionally be assigned a MAC address, MTU, and IEEE 802.1Q mode (tagged or access). Each interface can also be enabled or disabled, and optionally designated as management-only (for out-of-band management).

The following operational statuses are available by default:

* Planned
* Maintenance
* Active
* Decommissioning
* Failed

+++ 1.4.0
    - Added `bridge` field.
    - Added `parent_interface` field.
    - Added `status` field.

Interfaces may be physical or virtual in nature, but only physical interfaces may be connected via cables. Cables can connect interfaces to pass-through ports, circuit terminations, or other interfaces.

Physical interfaces may be arranged into a link aggregation group (LAG) and associated with a parent LAG (virtual) interface. LAG interfaces can be recursively nested to model bonding of trunk groups. Like all virtual interfaces, LAG interfaces cannot be connected physically.

+/- 2.0.0
    The relationship to IP addresses has been changed to a many-to-many relationship. This allows an IP address to be assigned to multiple interfaces, and an interface to have multiple IP addresses assigned to it.

IP addresses can be assigned to interfaces. VLANs can also be assigned to each interface as either tagged or untagged. (An interface may have only one untagged VLAN.)

!!! note
    Although devices and virtual machines both can have interfaces, a separate model is used for each. Thus, device interfaces have some properties that are not present on virtual machine interfaces and vice versa.

+++ 1.4.5
    The fields `created` and `last_updated` were added to all device component models. If you upgraded from Nautobot 1.4.4 or earlier, the values for these fields will default to `None` (null).

+++ 1.6.0
    Interfaces can now be assigned to an [Interface Redundancy Group](./interfaceredundancygroup.md) to represent redundancy protocols such as HSRP or VRRP.
