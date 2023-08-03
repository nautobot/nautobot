# IPAM

## Replace Aggregate with Prefix

`Aggregate` models are removed in v2.0 and all existing `Aggregate` instances are migrated to `Prefix` with type set to "Container". So your models and data that are associated with `Aggregate` via ForeignKey or ManyToMany relationships are now required to be migrated to `Prefix`. Please go [here](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md) for this change and its potential impact on other models.

## Introduction of Namespace

A namespace groups together a set of related but distinct [VRFs](../../../user-guide/core-data-model/ipam/vrf.md), [prefixes](../../../user-guide/core-data-model/ipam/prefix.md), and [IP addresses](../../../user-guide/core-data-model/ipam/ipaddress.md). Within a given namespace, only a single record may exist for each distinct VRF, prefix, or IP address. Although such a record may be used in multiple locations within your network, such as a VRF being configured on multiple devices, or a virtual IP address being assigned to multiple interfaces or devices, it is fundamentally a single network object in these cases, and Nautobot models this data accordingly. Check out the model documentation [here](../../../user-guide/core-data-model/ipam/namespace.md)

## Concrete Relationship between Prefix and IP Address

[IP addresses](../../../user-guide/core-data-model/ipam/ipaddress.md) now have a concrete relationship with its parent [Prefix](../../../user-guide/core-data-model/ipam/prefix.md). `IPAddress.parent` now refers to the parent prefix and `Prefix.ip_addresses` refers to the child ips.`

## Concrete Relationship between Prefix and Self

[Prefixes](../../../user-guide/core-data-model/ipam/prefix.md) now has a concrete parent/child relationship with itself. `Prefix.parent` refers to its parent prefix and `Prefix.children` refers to all its child prefixes.

## Convert Relationship Type between Prefix and VRF to Many to Many

[Prefixes](../../../user-guide/core-data-model/ipam/prefix.md) now no longer has a ForeignKey to [VRF](../../../user-guide/core-data-model/ipam/vrf.md). Instead, the Many to Many relationship is now defined on the VRF side as `VRF.prefixes`. VRF is no longer assigned to an IPAddress and is now on the parent Prefix. It is now a M2M relationship between the VRF and Prefix. VRF is also no longer a uniqueness constraint on the Prefix. Namespace is used instead. There is a default `Global` Namespace that all Prefixes are migrated into from 1.x.
