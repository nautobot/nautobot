# Prefixes

A prefix is an IPv4 or IPv6 network and mask expressed in CIDR notation (e.g. "192.0.2.0/24"). A prefix entails only the "network portion" of an IP address: All bits in the address not covered by the mask must be zero. (In other words, a prefix cannot be a specific IP host address, except in the case of /32 IPv4 prefixes and /128 IPv6 prefixes.)

At the database level, a prefix stores its network information in the fields `network`, `broadcast`, `prefix_length`, and `ip_version`. For convenience, the Nautobot UI, REST API, and Django ORM permit defining all of these via a single `prefix` parameter as an alternative.

Each prefix belongs to a specific [Namespace](namespace.md), and is unique within that namespace. Each prefix can also optionally be assigned to a particular [Location(s)](../dcim/location.md), as well as to zero or more [virtual routing and forwarding (VRF)](vrf.md) instances. All prefixes not assigned to a VRF are considered to be in the "global" VRF within their namespace.

+/- 2.0.0 "Prefixes are unique per Namespace"
    In Nautobot 1.x, prior to the introduction of the namespace data model, a prefix might or might not be unique within its assigned VRF. In Nautobot 2.0, prefixes are always unique within their namespace. You may need to do some cleanup of your data after migrating from Nautobot 1.x to suit the new data requirements.

+/- 2.2.0 "Prefixes can now be assigned to multiple Locations"
    A Prefix can now be assigned to multiple Locations if desired.

Each prefix must be assigned a [`status`](../../platform-functionality/status.md) and can optionally be assigned a [`role`](../../platform-functionality/role.md). These terms are often used interchangeably so it's important to recognize the difference between them. The **status** defines a prefix's operational state. The following statuses are provided by default:

* Active - Provisioned and in use
* Reserved - Designated for future use
* Deprecated - No longer in use

+/- 2.0.0 "Introduction of `type` field"
    The "Container" status was removed and its functionality was replaced by the `Prefix.type` field ([see below](#prefix-types)).

On the other hand, a prefix's **role** defines its function. Role assignment is optional and roles are fully customizable. For example, you might create roles to differentiate between production and development infrastructure.

A prefix may also be assigned to a [VLAN](vlan.md). This association is helpful for associating address space with layer two domains. A VLAN may have multiple prefixes assigned to it.

A prefix can be assigned to an [RIR](rir.md) to track which RIR has granted your organization permission to use the specified IP space on the public Internet.

The `date_allocated` field can be used to track any date and time you would like to define as the "allocated date" for a prefix. This could be the date an RIR assigned a prefix to your organization or the date a prefix was assigned to a specific internal team.

+++ 2.0.0 "Introduction of `date_allocated` and `rir` fields"
    The `date_allocated` and `rir` fields were added, migrating data from the removed `Aggregate` model.

## Prefix and IP Address Hierarchy

The hierarchy of prefixes and their constituent [IP addresses](ipaddress.md) is tracked in the Nautobot database via `parent` foreign keys. For example you might have in a given namespace:

* Prefix 10.0.0.0/8 (with no `parent`)
    * IP address 10.0.1.0/32 (with `parent` 10.0.0.0/8)
    * Prefix 10.1.1.0/24 (with `parent` 10.0.0.0/8)
        * IP address 10.1.1.1/24 (with `parent` 10.1.1.0/24)

Note that in Nautobot, all IP addresses *must* have a parent prefix; "orphaned" IP addresses are not permitted.

In most cases, you will not need to ever explicitly specify the `parent` value yourself, as specifying the `namespace` is generally more user-friendly and will result in the `parent` being automatically determined and updated as needed by Nautobot.

### Hierarchy Updates when Editing Prefixes

When editing a Prefix and changing its `prefix` value (`network`, `prefix_length`, etc.), or `namespace`, Nautobot will automatically update the `parent` field of the record and related Prefix and IP Address records as needed to preserve the correct hierarchy. **Such edits to a Prefix do _not_ "renumber" or "re-IP" the descendant Prefixes and IP Addresses below this Prefix.** For example, if the aforementioned 10.1.1.0/24 Prefix were edited to have a `network` of 10.**0**.1.0/24, IP address 10.1.1.1/24 would be updated such that its `parent` was now the 10.0.0.0/8 Prefix, as 10.0.1.0/24 does not contain host 10.1.1.1, but 10.0.0.0/8 does. Similarly, IP address 10.0.1.0/32 would be updated to have its `parent` become the newly updated 10.0.1.0/24 Prefix:

* Prefix 10.0.0.0/8 (with no `parent`)
    * Prefix ~~10.1.1.0/24~~ _10.0.1.0/24_ (with `parent` 10.0.0.0/8)
        * IP address 10.0.1.0/32 (with `parent` ~~10.0.0.0/8~~ _10.0.1.0/24_)
    * IP address 10.1.1.1/24 (with `parent` ~~10.1.1.0/24~~ _10.0.0.0/8_)

??? warning "Orphaned IP addresses"
    If editing an existing Prefix would result in some of its child IP Addresses becoming "orphans" with no valid `parent` Prefix, Nautobot will raise a validation error and reject the change with an appropriate explanation.

Additionally, when changing a Prefix's `namespace`, not only the specified Prefix record, but *also all of its descendant Prefix records* will be moved into the new Namespace. This is in service of the "principle of least surprise", because IP Address records do not have their own individual Namespaces but instead derive their namespace from their `parent` Prefixes, and it would be surprising to most users if only IPs directly under a given Prefix were brought along, while IPs under a nested subnet Prefix were left behind in the original Namespace.

??? warning "Uniqueness violations when changing Namespace"
    Because Prefix and IP Address uniqueness is enforced per-Namespace, if the target Namespace already contains existing Prefix and/or IP Address records, moving a Prefix and its descendants into that Namespace may result in data "collision" and violations of the uniqueness constraint. Nautobot will detect such a scenario and prevent the change.

??? warning "VRFs are specific to a Namespace"
    Because VRFs are specific to a Namespace, moving a Prefix *that's associated to one or more VRFs* into a different Namespace is blocked by Nautobot, and will result in a validation error with a message about needing to disassociate the Prefix (and its descendants) from VRFs before changing the Namespace. The workflow you'd need to follow here would be:

    1. Disassociate the Prefix and its descendant Prefixes from any and all VRFs in the initial Namespace.
    2. Move the Prefix (and implicitly its descendants) into the target Namespace.
    3. Create and/or associate VRFs in the target Namespace to the Prefix(es) as desired.

    If you find yourself needing to perform this workflow frequently, consider implementing a simple Nautobot [Job](../../platform-functionality/jobs/index.md) to consolidate these three steps into a single repeatable task.

## Prefix Types

The prefix model can be set to one of three types through the `type` field. The valid prefix types are:

* Container
* Network (default)
* Pool

We recommend that you think of "Networks" as the actual host-containing subnets in your network, while "Containers" represent groups of related "Networks", and "Pools" are used as needed within a "Network". In other words, "Containers" contain "Networks" which may contain "Pools". However, Nautobot does not strictly enforce this hierarchy. There are however a few ways in which different prefix types behave differently, as described below.

+/- 2.0.0 "Removal of `is_pool` field"
    The `is_pool` field was removed and its functionality was replaced by the `Prefix.type` field.

### Allocatable Hosts by Prefix Type

If a prefix's `type` is set to "Pool", Nautobot will treat this prefix as a range (such as a NAT pool) wherein every IP address is valid and assignable. This logic is used when identifying available IP addresses within a prefix. If `type` is set to "Network" or "Container", Nautobot will assume that the first and last (network and broadcast) addresses within an IPv4 prefix are unusable as hosts.

### Prefix Utilization Calculation by Prefix Type

* If the prefix `type` is "Container", the utilization is calculated as the sum of the total address space of all child prefixes. Individual IP addresses are not included in the calculation.
* Conversely, if the prefix `type` is "Pool", the utilization is calculated as the sum of the total number of IP addresses within the pool's range. Prefixes are not included in the calculation.
* If the prefix `type` is "Network":
    * The utilization is calculated as the sum of the total address space of all child prefixes plus the total number of child IP addresses not covered by a child prefix.
    * For IPv4 networks larger than /31, if neither the first (network) or last (broadcast) address is occupied by either a pool or an IP address, they are subtracted from the total size of the prefix.
