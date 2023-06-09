# Prefixes

A prefix is an IPv4 or IPv6 network and mask expressed in CIDR notation (e.g. 192.0.2.0/24). A prefix entails only the "network portion" of an IP address: All bits in the address not covered by the mask must be zero. (In other words, a prefix cannot be a specific IP address.)

Each prefix can be assigned to a particular site (optionally also to a location within the site) and a virtual routing and forwarding instance (VRF). Each VRF represents a separate IP space or routing table. All prefixes not assigned to a VRF are considered to be in the "global" table.

Each prefix must be assigned a [`status`](../../models/extras/status.md) and can optionally be assigned a role. These terms are often used interchangeably so it's important to recognize the difference between them. The **status** defines a prefix's operational state. The following statuses are provided by default:

* Active - Provisioned and in use
* Reserved - Designated for future use
* Deprecated - No longer in use

+/- 2.0.0
    The "Container" status was removed and its functionality was replaced by the `Prefix.type` field.

On the other hand, a prefix's **role** defines its function. Role assignment is optional and roles are fully customizable. For example, you might create roles to differentiate between production and development infrastructure.

A prefix may also be assigned to a VLAN. This association is helpful for associating address space with layer two domains. A VLAN may have multiple prefixes assigned to it.

The prefix model can be set to one of three types through the `type` field. The valid prefix types are:

* Container
* Network (default)
* Pool

If a prefix's type is set to "Pool", Nautobot will treat this prefix as a range (such as a NAT pool) wherein every IP address is valid and assignable. This logic is used when identifying available IP addresses within a prefix. If type is set to "Container" or "Network", Nautobot will assume that the first and last (network and broadcast) addresses within an IPv4 prefix are unusable.

+/- 2.0.0
    The `is_pool` field was removed and its functionality was replaced by the `Prefix.type` field.

A prefix can be assigned to an [RIR](rir.md) to track which RIR has granted your organization permission to use the specified IP space on the public Internet.

The `date_allocated` field can be used to track any date and time you would like to define as the "allocated date" for a prefix. This could be the date an RIR assigned a prefix to your organization or the date a prefix was assigned to a specific internal team.

+++ 2.0.0
    The `date_allocated` and `rir` fields were added, migrating data from the removed `Aggregate` model.

## Prefix utilization calculation

+/- 2.0.0

The `get_utilization` method on the `ipam.Prefix` model has been updated in 2.0 to account for the `Prefix.type` field. The behavior is now as follows:

* If the `Prefix.type` is `Container`, the utilization is calculated as the sum of the total address space of all child prefixes.
* If the `Prefix.type` is `Pool`, the utilization is calculated as the sum of the total number of IP addresses within the pool's range.
* If the `Prefix.type` is `Network`:
    * The utilization is calculated as the sum of the total address space of all child `Pool` prefixes plus the total number of child IP addresses.
    * For IPv4 networks larger than /31, if neither the first or last address is occupied by either a pool or an IP address, they are subtracted from the total size of the prefix.
