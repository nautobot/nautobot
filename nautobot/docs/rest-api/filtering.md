# REST API Filtering

## Filtering Objects

The objects returned by an API list endpoint can be filtered by attaching one or more query parameters to the request URL. For example, `GET /api/dcim/sites/?status=active` will return only sites with a status of "active."

Multiple parameters can be joined to further narrow results. For example, `GET /api/dcim/sites/?status=active&region=europe` will return only active sites within the Europe region.

Generally, passing multiple values for a single parameter will result in a logical OR operation. For example, `GET /api/dcim/sites/?region=north-america&region=south-america` will return sites in North America _or_ South America. However, a logical AND operation will be used in instances where a field may have multiple values, such as tags. For example, `GET /api/dcim/sites/?tag=foo&tag=bar` will return only sites which have both the "foo" _and_ "bar" tags applied.

+/- 1.4.0
    If [STRICT_FILTERING](../configuration/optional-settings.md#strict_filtering) is True (its default value), unrecognized filter parameters now result in a 400 Bad Request response instead of being silently ignored.

### Filtering by Choice Field

Some models have fields which are limited to specific choices, such as the `status` field on the Prefix model. To find all available choices for this field, make an authenticated `OPTIONS` request to the model's list endpoint, and use `jq` to extract the relevant parameters:

```no-highlight
curl -s -X OPTIONS \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
http://nautobot/api/ipam/prefixes/ | jq ".actions.POST.status.choices"
```

Example output:

```json
[
  {
    "value": "container",
    "display": "Container"
  },
  {
    "value": "active",
    "display": "Active"
  },
  {
    "value": "reserved",
    "display": "Reserved"
  },
  {
    "value": "deprecated",
    "display": "Deprecated"
  }
]
```

!!! note
    The above works only if the API token used to authenticate the request has permission to make a `POST` request to this endpoint.

### Filtering by Custom Field

To filter results by a custom field value, prepend `cf_` to the custom field name. For example, the following query will return only sites where a custom field named `foo` is equal to 123:

```no-highlight
GET /api/dcim/sites/?cf_foo=123
```

!!! note
    For custom field filters, due to historical details of implementation, only a single filter value can be specified when matching a given field. In other words, in the above example, you could _not_ add `&cf_foo=456` to the query in order to get all sites where custom field `foo` is 123 _or_ 456; instead you would need to run two separate queries. This restriction does not apply to custom field filters using lookup expressions (next section) and will likely be changed in a future major version of Nautobot.

Custom fields can be mixed with built-in fields to further narrow results. When creating a custom string field, the type of filtering selected (loose versus exact) determines whether partial or full matching is used.

+++ 1.4.0
    Custom fields can use the lookup expressions listed in the next section by prepending `cf_` to the custom field `name` (and not the `slug`) followed by the required lookup type (see below).

## Lookup Expressions

Certain model fields (including, in Nautobot 1.4.0 and later, custom fields of type `text`, `url`, `select`, `integer`, and `date`) also support filtering using additional lookup expressions. This allows
for negation and other context-specific filtering.

These lookup expressions can be applied by adding a suffix to the desired field's name, e.g. `mac_address__n`. In this case, the filter expression is for negation and it is separated by two underscores. Below are the lookup expressions that are supported across different field types.

### Numeric Fields

Numeric-based fields (ASN, VLAN ID, etc.) support these lookup expressions:

- `n` - not equal to (negation)
- `lt` - less than
- `lte` - less than or equal
- `gt` - greater than
- `gte` - greater than or equal

### String Fields

String-based (char) fields (Name, Address, etc.) support these lookup expressions:

- `n` - not equal to (negation)
- `ic` - case-insensitive contains
- `nic` - negated case-insensitive contains
- `isw` - case-insensitive starts-with
- `nisw` - negated case-insensitive starts-with
- `iew` - case-insensitive ends-with
- `niew` - negated case-insensitive ends-with
- `ie` - case-insensitive exact match
- `nie` - negated case-insensitive exact match

+++ 1.3.0
    - `re` - case-sensitive regular expression match
    - `nre` - negated case-sensitive regular expression match
    - `ire` - case-insensitive regular expression match
    - `nire` - negated case-insensitive regular expression match

### Foreign Keys & Other Fields

Certain other fields, namely foreign key relationships support just the negation
expression: `n`.

### Network and Host Fields

There are [Custom Lookups](https://docs.djangoproject.com/en/3.2/howto/custom-lookups/) built for the `VarbinaryIPField` field types. While
the `VarbinaryIPField` is applied to fields for network, host, and broadcast, the below filters only apply to network and host. The design
makes an assumption that there is in fact a broadcast (of type `VarbinaryIPField`) and prefix_length (of type `Integer`) within the same
model. This assumption is used to understand the relevant scope of the network in question and is important to note when extending the
Nautobot core or plugin data model.

- `**` `exact` - An exact match of an IP or network address, e.g. `host__exact="10.0.0.1"`
- `**` `iexact` - An exact match of an IP or network address, e.g. `host__iexact="10.0.0.1"`
- `**` `startswith` - Determine if IP or network starts with the value provided, e.g. `host__startswith="10.0.0."`
- `**` `istartswith` - Determine if IP or network starts with the value provided, e.g. `host__istartswith="10.0.0."`
- `**` `endswith` - Determine if IP or network ends with the value provided, e.g. `host__endswith="0.1"`
- `**` `iendswith` - Determine if IP or network ends with the value provided, e.g. `host__iendswith="0.1"`
- `**` `regex` - Determine if IP or network matches the pattern provided, e.g. `host__regex=r"10\.(.*)\.1`
- `**` `iregex` - Determine if IP or network matches the pattern provided, e.g. `host__iregex=r"10\.(.*)\.1`
- `net_contained` - Given a network, determine which networks are contained within the provided e.g. `network__net_contained="192.0.0.0/8"` would include 192.168.0.0/24 in the result
- `net_contained_or_equal` - Given a network, determine which networks are contained or is within the provided e.g. `network__net_contained_or_equal="192.0.0.0/8"` would include 192.168.0.0/24 and 192.0.0.0/8 in the result
- `net_contains` - Given a network, determine which networks contain the provided network e.g. `network__net_contains="192.168.0.0/16"` would include 192.0.0.0/8 in the result
- `net_contains_or_equals` - Given a network, determine which networks contain or is the provided network e.g. `network__net_contains="192.168.0.0/16"` would include 192.0.0.0/8 and 192.168.0.0/16 in the result
- `net_equals` - Given a network, determine which which networks are an exact match. e.g. `network__net_equals="192.168.0.0/16"` would include only 192.168.0.0/16 in the result
- `net_host` - Determine which networks are parent of the provided IP, e.g. `host__net_host="10.0.0.1"` would include 10.0.0.1/32 and 10.0.0.0/24 in the result
- `net_host_contained` - Given a network, select IPs whose host address (regardless of its subnet mask) falls within that network , e.g. `host__net_host_contained="10.0.0.0/24"` would include hosts 10.0.0.1/8 and 10.0.0.254/32 in the result
- `net_in` - Given a list of networks, select addresses (regardless of their subnet masks) within those networks, e.g. `host__net_in=["10.0.0.0/24", "2001:db8::/64"]` would include hosts 10.0.0.1/16 and 2001:db8::1/65 in the result
- `family` - Given an IP address family of 4 or 6, provide hosts or networks that are that IP version type, e.g. `host__family=6` would include 2001:db8::1 in the result

> Note: The fields denoted with `**` are only supported in the MySQL dialect (and not Postgresql) at the current time.
