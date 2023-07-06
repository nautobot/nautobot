# Virtual Routing and Forwarding (VRF)

A VRF object in Nautobot represents a virtual routing and forwarding (VRF) domain. Each VRF is essentially a separate routing table. VRFs are commonly used to isolate customers or organizations from one another within a network, or to route overlapping address space (e.g. multiple instances of the 10.0.0.0/8 space). Each VRF may be assigned to a specific tenant to aid in organizing the available IP space by customer or internal user.

+/- 2.0.0
    Each VRF now belongs to a [namespace](namespace.md), which now serves as the uniqueness boundary for address space, similar to how a VRF with the "enforce unique" flag set behaved in Nautobot 1.x. Prefix and address uniqueness is enforced by the namespace now (regardless of VRF association within that namespace) and the "enforce unique" flag has been removed from VRFs.

Each VRF is assigned a name and an optional route distinguisher (RD). The RD is expected to take one of the forms prescribed in [RFC 4364](https://tools.ietf.org/html/rfc4364#section-4.2), however its formatting is not strictly enforced. Any given RD is unique within a namespace; in a future Nautobot release, VRF names will also be enforced to be unique per namespace.

Each VRF may have one or more import and/or export route targets applied to it. Route targets are used to control the exchange of routes (prefixes) among VRFs in L3VPNs.

Prefixes (and, implicitly, their contained IP addresses) can be assigned to zero or more VRFs in their namespace, as best suits their usage within your network. Any prefix or IP address not assigned to a VRF is said to belong to the "global" VRF within their namespace. It's important to distinguish this from the "global" namespace that you may have defined and which may contain any number of distinct VRFs.

+/- 2.0.0
    In Nautobot 1.x, each prefix could only be assigned to at most one VRF, and you would have to create multiple prefix records in the database to reflect a prefix's existence in multiple VRFs. On migrating existing data to Nautobot 2.0, you may need to do some cleanup of your IPAM data to fit the new models.
