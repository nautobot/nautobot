# Interfaces

Virtual machine interfaces behave similarly to device interfaces, and can be assigned IP addresses, VLANs, an operational [`status`](../../platform-functionality/status.md) and services. However, given their virtual nature, they lack properties pertaining to physical attributes. For example, VM interfaces do not have a physical type and cannot have cables attached to them.

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

+/- 2.0.0
    The relationship to IP addresses has been changed to a many-to-many relationship. This allows an IP address to be assigned to multiple VM interfaces, and a VM interface to have multiple IP addresses assigned to it.
