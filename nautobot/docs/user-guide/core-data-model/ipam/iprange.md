# IP Range

An IP Range represents a contiguous span of IP addresses, defined by a start address and an end address (both inclusive), that share a single parent Prefix. Unlike a Prefix, an IP Range is not a network and has no mask, it is simply two bare host addresses marking the boundaries of a span. This makes IP Ranges well suited to representing blocks of addresses that have a specific purpose but do not align to a CIDR boundary, without having to create an individual IP Address record for every address in the span.

Common uses:

- include DHCP scopes (for example, `10.10.1.50–10.10.1.200`)
- reserved or exclusion zones for network appliances (for example, `192.168.1.1–192.168.1.9`)
- NAT pools (for example, `203.0.113.64–203.0.113.95`)

## Parent Prefix and Namespace

Every IP Range belongs to a single parent Prefix that fully contains it. In most cases you will not specify the parent directly; instead you specify a Namespace (or rely on the default), and Nautobot determines the appropriate parent Prefix automatically from the range's start and end addresses. Both the start and end address must resolve to the same parent Prefix. If no single existing Prefix contains the entire span, the range cannot be created, and you will need to create a wider parent Prefix first.

Because an IP Range derives its Namespace from its parent Prefix, ranges are not assigned to a Namespace or VRF directly; they inherit these from the parent, in the same way IP Addresses do.

## Status and Role

Each IP Range can be assigned an operational status and an optional functional role. The default statuses available are the same as those available for IP Addresses. Roles are used to indicate the purpose of a range. A starter set of roles is provided (DHCP, Firewall Object, NAT Pool, LB Pool, and Reserved), and you may define additional roles as needed.

## Utilization

By default, an IP Range does not affect the utilization of its parent Prefix on its own only IP Addresses created within the parent contribute to utilization. If you enable **Mark as fully utilized** (`count_as_utilized`), the entire span of the range is counted toward the parent Prefix's utilization, regardless of how many individual IP Addresses exist within it. This is useful for representing a DHCP scope or reserved block as occupied space even when no individual addresses have been recorded.

When a range is marked as fully utilized but is not exclusive, any IP Addresses created within the range are not double-counted: the addresses are already represented by the range, so they do not add to utilization a second time.

## Exclusive Ranges

An IP Range can be marked as **Exclusive** (`is_exclusive`). When a range is exclusive, individual IP Address objects may not be created within its span — attempting to do so raises a validation error. This is useful for protecting reserved blocks from having conflicting individual addresses defined.

A non-exclusive range, by contrast, permits IP Addresses to be created within it.

You cannot mark a range as exclusive if IP Addresses already exist within its span. Those addresses must be removed first.

## Validation Rules

Nautobot enforces the following rules when an IP Range is created or edited:

- The start and end addresses must be of the same IP version.
- The start address must be less than or equal to the end address.
- Both the start and end address must be contained within a single common parent Prefix.
- The range must not intersect any other IP Range in the same Namespace.
- An exclusive range must not contain any existing IP Address.
- The range must not overlap any child Prefix of its parent Prefix.

In addition, editing a Prefix in a way that would leave a contained IP Range no longer fully within the Prefix is blocked. The range must be modified or deleted first. Likewise, creating an IP Address that falls within an exclusive IP Range is blocked.

## Notes

IP Ranges do not automatically create or manage individual IP Address records within their span; a range is a single record describing a span, not a container of addresses.
