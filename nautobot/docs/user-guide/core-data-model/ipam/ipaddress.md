# IP Addresses

An IP address comprises a single `host` address (either IPv4 or IPv6) and its associated subnet `mask_length`, which should match exactly how the IP address is configured on an interface in the real world. For convenience, these two database fields are often available together as a single CIDR `address` string as well, such as "10.1.2.3/32" (equivalent to `host` "10.1.2.3" and `mask_length` 32).

!!! tip "Host is immutable"
    The `host` value for a given IP address record cannot be changed once it is created and saved to the database. It is however permissible to change the `mask_length` as needed. For scenarios such as re-allocation of network space, the recommended workflow is to create a new record for the new `host` value, then delete the old record.

IP addresses are automatically arranged under their `parent` [Prefixes](prefix.md) according to the IP hierarchy.

+++ 2.0.0 "IP Address to Prefix is now a concrete foreign-key relationship"
    Parenting of IP addresses under Prefixes is now automatically managed at the database level to greatly improve performance especially when calculating tree hierarchy and utilization. Refer to the [Prefix](prefix.md) documentation for more details about this functionality.

IP addresses are not directly assigned to [Namespaces](namespace.md) or [VRFs](vrf.md) in the database on an individual basis, but instead derive their namespace and VRF(s) from their parent prefix. For convenience, the Nautobot UI, REST API, and Django ORM do present a virtual `namespace` field on IP addresses, as (especially when creating a new IP address record) it is often more straightforward to specify the `namespace` of an IP address, and let Nautobot automatically determine the correct `parent` in that namespace, than to specify the `parent` directly.

+/- 2.0.0 "All IP addresses must belong to a parent Prefix"
    In Nautobot 1.x, IP addresses were only loosely associated to prefixes, and it was possible to create "orphan" IP addresses that had no corresponding prefix record. In Nautobot 2.0 this is no longer the case; each IP address has a parent prefix, and you can no longer create IP addresses that do not belong to a defined prefix and namespace. When migrating existing data from Nautobot 1.x, parent prefixes will be automatically created where needed, but you may need to do some additional cleanup of your IPAM data after the migration in order to ensure its accuracy and correctness.

Each IP address can also be assigned an operational [`status`](../../platform-functionality/status.md) and a functional [`role`](../../platform-functionality/role.md).  The following statuses are available by default:

* Active
* Reserved
* Deprecated

Roles are used to indicate some special attribute of an IP address; for example, use as a loopback or as the the virtual IP for a VRRP group. The following roles are available by default:

* Loopback
* Secondary
* Anycast
* VIP
* VRRP
* HSRP
* GLBP

Types are used to indicate special functions of an IP address such as DHCP or SLAAC. The default is "host":

* Host
* DHCP
* SLAAC (IPv6 Stateless Address Autoconfiguration)

+/- 2.0.0 "One IP Address, multiple interfaces"
    The relationship to device and virtual machine interfaces has been changed to a many-to-many relationship. This allows a single IP address record to be assigned to multiple interfaces simultaneously if desired for scenarios such as IP Anycast.

An IP address can be assigned to device or virtual machine interfaces, and an interface may have multiple IP addresses assigned to it. Further, each device and virtual machine may have one of its interface IPs designated as its primary IP per address family (one for IPv4 and one for IPv6).

!!! note "Preferring IPv4 or IPv6 primary IPs"
    When primary IPs are set for both IPv4 and IPv6, Nautobot will prefer IPv6. This can be changed by setting the `PREFER_IPV4` configuration parameter.

## Network Address Translation (NAT)

An IP address can be designated as the network address translation (NAT) inside IP address for one or more other IP addresses. This is useful primarily to denote a translation between public and private IP addresses. This relationship is followed in both directions: For example, if 10.0.0.1 is assigned as the inside IP for 192.0.2.1, 192.0.2.1 will be displayed as the outside IP for 10.0.0.1.

## De-duplicating IPAddresses

+++ 2.0.0

In Nautobot 2.0.0 and later, IP Addresses must now be unique per Namespace. As a consequence, data migrations from Nautobot 1.x (where in some cases IP Addresses were permitted to be duplicated) will, as needed, move duplicate IP Addresses to a number of "cleanup" Namespaces in order to avoid uniqueness violations within the global Namespace. In many cases these duplicate IP Address records can be collapsed into single records (in particular, because Nautobot 2.x permits assignment of a single IP Address to multiple Interfaces, whereas Nautobot 1.x did not permit this). To assist with such efforts, Nautobot provides an [IP Address Merge tool](../../feature-guides/ip-address-merge-tool.md).
