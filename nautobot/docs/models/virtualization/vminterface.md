# Interfaces

Virtual machine interfaces behave similarly to device interfaces, and can be assigned IP addresses, VLANs, an operational [`status`](../../models/extras/status.md) and services. However, given their virtual nature, they lack properties pertaining to physical attributes. For example, VM interfaces do not have a physical type and cannot have cables attached to them.

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
