# VLANs

A VLAN represents an isolated layer two domain, identified by a name and a numeric ID (1-4094) as defined in [IEEE 802.1Q](https://en.wikipedia.org/wiki/IEEE_802.1Q). Each VLAN may be assigned to a site, tenant, and/or VLAN group.

Each VLAN must be assigned one of the following operational [`statuses`](https://nautobot.readthedocs.io/en/latest/models/extras/status/):

* Active
* Reserved
* Deprecated

Status fields can now be customized via the new [`status`](https://nautobot.readthedocs.io/en/latest/models/extras/status/) model.

As with prefixes, each VLAN may also be assigned a functional role. Prefixes and VLANs share the same set of customizable roles.
