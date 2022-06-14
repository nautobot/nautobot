# Interfaces

Virtual machine interfaces behave similarly to device interfaces, and can be assigned IP addresses, VLANs, an operational [`status`](https://nautobot.readthedocs.io/en/stable/models/extras/status/) and services. However, given their virtual nature, they lack properties pertaining to physical attributes. For example, VM interfaces do not have a physical type and cannot have cables attached to them.

_Added in 1.4.0: `status` field_

The following operational statuses are available by default:

* Planned
* Maintenance
* Active
* Decommissioning
* Failed
