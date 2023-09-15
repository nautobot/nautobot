# IP Addresses

An IP address comprises a single host address (either IPv4 or IPv6) and its subnet mask. Its mask should match exactly how the IP address is configured on an interface in the real world.

IP addresses are automatically arranged under parent prefixes according to the IP hierarchy. IP addresses are not directly assigned to namespaces or VRFs on an individual basis, but instead derive their namespace and VRF(s) from their parent prefix.

+/- 2.0.0
    In Nautobot 1.x, IP addresses were only loosely associated to prefixes, and it was possible to create "orphan" IP addresses that had no corresponding prefix record. In Nautobot 2.0 this is no longer the case; each IP address has a parent prefix, and you can no longer create IP addresses that do not belong to a defined prefix and namespace. When migrating existing data from Nautobot 1.x, parent prefixes will be automatically created where needed, but you may need to do some additional cleanup of your IPAM data after the migration in order to ensure its accuracy and correctness.

Each IP address can also be assigned an operational [`status`](../../platform-functionality/status.md) and a functional role.  The following statuses are available by default:

* Active
* Reserved
* Deprecated

Roles are used to indicate some special attribute of an IP address; for example, use as a loopback or as the the virtual IP for a VRRP group. (Note that functional roles are conceptual in nature, and thus cannot be customized by the user.) Available roles include:

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

+/- 2.0.0
    The relationship to device and virtual machine interfaces has been changed to a many-to-many relationship. This allows an IP address to be assigned to multiple interfaces, and an interface to have multiple IP addresses assigned to it.

An IP address can be assigned to device or virtual machine interfaces, and an interface may have multiple IP addresses assigned to it. Further, each device and virtual machine may have one of its interface IPs designated as its primary IP per address family (one for IPv4 and one for IPv6).

!!! note
    When primary IPs are set for both IPv4 and IPv6, Nautobot will prefer IPv6. This can be changed by setting the `PREFER_IPV4` configuration parameter.

+/- 2.0.0
    `prefix_length` becomes `mask_length` and is intended to describe the desired subnet mask of the IP addresses when configured on interface(s).

## Network Address Translation (NAT)

An IP address can be designated as the network address translation (NAT) inside IP address for one or more other IP addresses. This is useful primarily to denote a translation between public and private IP addresses. This relationship is followed in both directions: For example, if 10.0.0.1 is assigned as the inside IP for 192.0.2.1, 192.0.2.1 will be displayed as the outside IP for 10.0.0.1.

+++ 1.3.0
    Support for multiple outside NAT IP addresses was added.

## IPAddress Parenting Concrete Relationship

+++ 2.0.0

The `ipam.IPAddress` model has been modified to have a foreign key to `ipam.Prefix` as the `parent` field. Parenting of IP addresses is now automatically managed at the database level to greatly improve performance especially when calculating tree hierarchy and utilization.

The following guidance has been added for the `IPAddress.parent` field:

* An `IPAddress` should have a parent `Prefix` of type `Network`
* An `IPAddress` should not be created if a suitable parent `Prefix` of type `Network` does not exist
* An `IPAddress` can be a member of a `Pool` but only if the `Pool` is a child of a `Network` prefix

!!! warning
    In a future Nautobot release, this guidance will become an enforced constraint on `IPAddress` creation and modification.

## De-duplicating IPAddresses

+++ 2.0.0

After upgrading to Nautobot v2.0, in order to satisfy new uniqueness constraints, the data migrations may duplicate `IP Addresses` across different `Namespaces`. Check out this [IP Address Merge tool](../../feature-guides/ip-address-merge-tool.md) to collapse unnecessarily duplicated `IP Addresses`.
