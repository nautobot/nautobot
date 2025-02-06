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

+/- 2.2.0
    - Replaced `location` ForeignKey field with `locations` ManyToManyField, allowing a VLAN to be assigned to multiple Locations.

## Modeling VLANs

With the update to Nautobot 2.2 that introduced the ability to have a single VLAN be associated to multiple locations, there needs to be some _recommended_ methods to model VLANs with the new functionality.

You should be looking to model VLANs in the same way that the layer 2 functionality is set up.

### Multiple Locations Using Same VLAN ID

In many organizations the use of cookiecutter like VLAN architecture is leveraged. In that a location may have VLAN30 be for the same purpose (ie Wireless, User, Voice) at each location. In this scenario, you should model a distinct VLAN30 in Nautobot for each Location. Creating a single VLAN and then associating it with multiple Locations would not accurately reflect the state of the layer 2 network.

### Multiple Locations, Stretched Layer 2

You would want to have a single VLAN that is associated with multiple Locations when the layer 2 environment is in fact stretched and devices within the VLAN are able to communicate via layer 2 mechanisms. Such designs include a campus network where you do have multiple Locations but a shared VLAN across all of them, for example wireless networks. Or in a data center fabric where the layer 2 is in fact stretched across the sites.
