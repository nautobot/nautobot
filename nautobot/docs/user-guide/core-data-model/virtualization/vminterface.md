# Interfaces

Virtual machine interfaces behave similarly to device interfaces, and can be assigned IP addresses, VLANs, an operational [`status`](../../platform-functionality/status.md), an operational [`role`](../../platform-functionality/role.md) and services. However, given their virtual nature, they lack properties pertaining to physical attributes. For example, VM interfaces do not have a physical type and cannot have cables attached to them.

The following operational statuses are available by default:

* Planned
* Maintenance
* Active
* Decommissioning
* Failed


+/- 2.0.0
    The relationship to IP addresses has been changed to a many-to-many relationship. This allows an IP address to be assigned to multiple VM interfaces, and a VM interface to have multiple IP addresses assigned to it.

+++ 2.3.0
    VMInterfaces now have an optional `role` field and can be assigned [Role](../../platform-functionality/role.md) instances to track common configurations.
