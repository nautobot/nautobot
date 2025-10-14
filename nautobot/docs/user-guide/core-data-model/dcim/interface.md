# Interfaces

Interfaces in Nautobot represent network interfaces used to exchange data with connected devices. On modern networks, these are most commonly Ethernet, but other types are supported as well. Each interface must be assigned a type, an operational [`status`](../../platform-functionality/status.md) and may optionally be assigned a MAC address, MTU, speed, duplex, IEEE 802.1Q mode (tagged or access) and an operational [`role`](../../platform-functionality/role.md). Each interface can also be enabled or disabled, and optionally designated as management-only (for out-of-band management).

The following operational statuses are available by default:

* Planned
* Maintenance
* Active
* Decommissioning
* Failed

## Speed and duplex

* `speed` (optional): Operational speed in Kbps as an integer. Value is rendered in the UI using human-readable units (e.g., Mbps/Gbps/Tbps).
* `duplex` (optional): Duplex setting for copper twisted‑pair interfaces. Accepted values are `auto`, `full`, or `half`.

### Validation rules

* LAG interfaces: do not support `speed` or `duplex`.
* Virtual and wireless interfaces: do not support `speed` or `duplex`.
* Optical/backplane and similar non‑copper types: do not support `duplex` (must be blank/null).
* Copper twisted‑pair types: `duplex` and `speed` may be set.

## Cabling

Interfaces may be physical or virtual in nature, but only physical interfaces may be connected via cables. Cables can connect interfaces to pass-through ports, circuit terminations, or other interfaces.

## LAGs

Physical interfaces may be arranged into a link aggregation group (LAG) and associated with a parent LAG (virtual) interface. LAG interfaces can be recursively nested to model bonding of trunk groups. Like all virtual interfaces, LAG interfaces cannot be connected physically. Interfaces can be assigned to an [Interface Redundancy Group](./interfaceredundancygroup.md) to represent redundancy protocols such as HSRP or VRRP.

+/- 2.0.0
    The relationship to IP addresses has been changed to a many-to-many relationship. This allows an IP address to be assigned to multiple interfaces, and an interface to have multiple IP addresses assigned to it.

IP addresses can be assigned to interfaces. VLANs can also be assigned to each interface as either tagged or untagged. (An interface may have only one untagged VLAN.)

!!! note
    Although devices and virtual machines both can have interfaces, a separate model is used for each. Thus, device interfaces have some properties that are not present on virtual machine interfaces and vice versa.

+++ 2.3.0
    Interfaces now have an optional `role` field and can be assigned [Role](../../platform-functionality/role.md) instances to track common configurations.

+/- 2.3.0
    This model has been updated to support being installed in [Modules](module.md). As a result, there are now two fields for assignment to a Device or Module. One of the `device` or `module` fields must be populated but not both. If a `module` is supplied, the `device` field must be null, and similarly the `module` field must be null if a `device` is supplied.
