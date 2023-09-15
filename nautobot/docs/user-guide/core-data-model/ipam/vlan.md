# VLANs

A VLAN represents an isolated layer two domain, identified by a name and a numeric ID (1-4094) as defined in [IEEE 802.1Q](https://en.wikipedia.org/wiki/IEEE_802.1Q). Each VLAN may be assigned to a location, tenant, and/or VLAN group.

Each VLAN must be assigned a [`status`](../../platform-functionality/status.md). The following statuses are available by default:

* Active
* Reserved
* Deprecated

As with prefixes, each VLAN may also be assigned a functional role. Prefixes and VLANs share the same set of customizable roles.

+/- 1.5.9
    The maximum `name` length was increased from 64 characters to 255 characters.

+/- 2.0.0
    - Renamed `group` field to `vlan_group`.
