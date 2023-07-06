# Namespaces

+++ 2.0.0

A namespace groups together a set of related but distinct [VRFs](vrf.md), [prefixes](prefix.md), and [IP addresses](ipaddress.md). Fundamentally, its purpose is to serve as a constraint or boundary for uniqueness and duplication of IPAM data. If you have a relatively straightforward network, where there are no overlapping prefixes or duplicated IP addresses, a single namespace may be sufficient to model your entire network, even if it has thousands of IPAM records; however, in the case of a managed service provider network or similar, you may need multiple namespaces to accurately model its complexities and clearly distinguish between otherwise seemingly-duplicate records.

Each namespace has a name and a description, and can optionally be associated to a location for informational purposes.

Within a given namespace, only a single record may exist for each distinct VRF, prefix, or IP address. Although such a record may be used in multiple locations within your network, such as a VRF being configured on multiple devices, or a virtual IP address being assigned to multiple interfaces or devices, it is fundamentally a single network object in these cases, and Nautobot models this data accordingly.

+/- 2.0.0
    This is a change from the Nautobot 1.x data model, in which, for example, each instance of a virtual IP address would typically need to be stored as a distinct database record. On migrating existing data from Nautobot 1.x you may need to do some cleanup of your IPAM data to fit the new models.

Namespaces exist in Nautobot to model the _exceptions_ to the above case, where a similarly-named VRF, or a prefix or IP address corresponding to the same subnet or host as another, is actually a distinct entity within your network and needs to be modeled as such. Another example where this might be necessary would be during a corporate merger, where perhaps the separate networks of each company might both use parts of the RFC 1918 `10.0.0.0/8` network space and need to coexist for a time as parallel network namespaces rather than parts of a single combined namespace.
