# IPAM

## Replace Aggregate with Prefix

`Aggregate` models are removed in v2.0 and all existing `Aggregate` instances are migrated to `Prefix` with type set to "Container". So your models and data that are associated with `Aggregate` via ForeignKey or ManyToMany relationships are now required to be migrated to `Prefix`. Please go [here](../../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#aggregate-migrated-to-prefix) for this change and its potential impact on other models.

## Introduction of Namespace

A Namespace groups together a set of related but distinct [VRFs](../../../../user-guide/core-data-model/ipam/vrf.md), [Prefixes](../../../../user-guide/core-data-model/ipam/prefix.md), and [IP addresses](../../../../user-guide/core-data-model/ipam/ipaddress.md). Within a given Namespace, only a single record may exist for each distinct VRF, Prefix, or IP address. Although such a record may be used in multiple locations within your network, such as a VRF being configured on multiple Devices, or a virtual IP address being assigned to multiple Interfaces or Devices, it is fundamentally a single network object in these cases, and Nautobot models this data accordingly. Check out the model documentation [here](../../../../user-guide/core-data-model/ipam/namespace.md)

## Concrete Relationship between Prefix and IP Address

[IP addresses](../../../../user-guide/core-data-model/ipam/ipaddress.md) now have a concrete relationship with its parent [Prefix](../../../../user-guide/core-data-model/ipam/prefix.md). `IPAddress.parent` now refers to the parent prefix and `Prefix.ip_addresses` refers to the child ips.`

## Concrete Relationship between Prefix and Self

Each [Prefix](../../../../user-guide/core-data-model/ipam/prefix.md) now has a concrete parent/child relationship with related Prefixes. `Prefix.parent` refers to its parent prefix and `Prefix.children` refers to all its child Prefixes.

## Convert Relationship Type between Prefix and VRF to Many to Many

[Prefixes](../../../../user-guide/core-data-model/ipam/prefix.md) now no longer have a ForeignKey to [VRF](../../../../user-guide/core-data-model/ipam/vrf.md). Instead, the Many to Many relationship is now defined on the VRF side as `VRF.prefixes`. VRF is also no longer a uniqueness constraint on the Prefix. Namespace is used instead.
Additionally, VRF is no longer assigned directly to an IPAddress but is now derived from any association to the parent Prefix.
