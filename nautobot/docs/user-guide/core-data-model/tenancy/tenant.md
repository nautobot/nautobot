# Tenants

A tenant represents a discrete grouping of resources used for administrative purposes. Typically, tenants are used to represent individual customers or internal departments within an organization. Many object types can be assigned to tenants, including:

* Circuits
* Clusters
* Devices
* Dynamic Groups
* IP addresses
* Locations
* Prefixes
* Racks
* Rack reservations
* Virtual machines
* VLANs
* VRFs

Tenant assignment is used to signify the ownership of an object in Nautobot. As such, each object may only be owned by a single tenant. For example, if you have a firewall dedicated to a particular customer, you would assign it to the tenant which represents that customer. However, if the firewall serves multiple customers, it doesn't *belong* to any particular customer, so tenant assignment would not be appropriate.

+/- 2.0.0
    - Renamed `group` field to `tenant_group`.
