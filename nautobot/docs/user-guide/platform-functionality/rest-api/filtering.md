# REST API Filtering

## Filtering Included Fields

Certain REST API fields can be expensive to look up or render, so Nautobot provides some capabilities to specify via query parameters whether to include or exclude such fields. Specifically, at this time, the following capabilities exist:

- `?include=config_context` - Device and Virtual Machine APIs only. Rendered [configuration context data](../../core-data-model/extras/configcontext.md) is not included by default, but can be added to these API responses by specifying this query parameter.
- `?include=relationships` - Any object supporting [Relationships](../relationship.md). Relationship data is not included by default, but can be added by specifying this query parameter.
- `?include=computed_fields` - Any object supporting [Computed Fields](../computedfield.md). Computed field values are not included by default, but can be added by specifying this query parameter.
- `?exclude_m2m=false` - Any object with many-to-many relations to another type of object. These related objects are excluded by default, but can be included (at the cost of performance) by specifying this query parameter.

+/- 2.0.0 "Changed config contexts to excluded by default, added `include=config_context` support"

+++ 2.4.0 "Added `exclude_m2m` support"

+/- 3.0.0 "Changed the default behavior of `exclude_m2m` to exclude many-to-many fields (except for `tags`, `content_types`, and `object_types`) by default"

## Filtering Objects

The objects returned by an API list endpoint can be filtered by attaching one or more query parameters to the request URL. For example, `GET /api/dcim/locations/?status=active` will return only locations with a status of "active."

Multiple parameters can be joined to further narrow results. For example, `GET /api/dcim/locations/?status=active&parent=europe&location_type=country` will return only active "country" type locations in Europe.

Generally, passing multiple values for a single parameter will result in a logical OR operation. For example, `GET /api/dcim/locations/?parent=north-america&parent=south-america&location_type=country` will return "country" type locations in North America _or_ South America. However, a logical AND operation will be used in instances where a field may have multiple values, such as tags. For example, `GET /api/dcim/locations/?tag=foo&tag=bar` will return only locations which have both the "foo" _and_ "bar" tags applied.

### Filtering by Choice Field

Some models have fields which are limited to specific choices, such as the `type` field on the Interface model. To find all available choices for this field, make an authenticated `OPTIONS` request to the model's list endpoint, and use `jq` to extract the relevant parameters:

```no-highlight
curl -s -X OPTIONS \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
http://nautobot/api/dcim/interfaces/ | jq ".actions.POST.type.choices"
```

Example output:

```json
[
  {
    "value": "virtual",
    "display": "Virtual"
  },
  {
    "value": "bridge",
    "display": "Bridge"
  },
  {
    "value": "lag",
    "display": "Link Aggregation Group (LAG)"
  },
  {
    "value": "100base-tx",
    "display": "100BASE-TX (10/100ME)"
  },
  {
    "value": "1000base-t",
    "display": "1000BASE-T (1GE)"
  },
...
```

!!! note
    The above works only if the API token used to authenticate the request has permission to make a `POST` request to this endpoint.

### Filtering by Custom Field

To filter results by a custom field value, prepend `cf_` to the custom field key. For example, the following query will return only locations where a custom field with key `foo` is equal to 123:

```no-highlight
GET /api/dcim/locations/?cf_foo=123
```

!!! note
    For custom field filters, due to historical details of implementation, only a single filter value can be specified when matching a given field. In other words, in the above example, you could _not_ add `&cf_foo=456` to the query in order to get all locations where custom field `foo` is 123 _or_ 456; instead you would need to run two separate queries. This restriction does not apply to custom field filters using lookup expressions (next section) and will likely be changed in a future major version of Nautobot.

Custom fields can be mixed with built-in fields to further narrow results. When creating a custom string field, the type of filtering selected (loose versus exact) determines whether partial or full matching is used.

+/- 2.0.0 "Custom field filters changed from `name` to `key` based"
    Custom field filters are now based on the custom field `key` string (in 1.x they used the field's `name`).

## Lookup Expressions

Certain model fields (including, in Nautobot 1.4.0 and later, custom fields of type `text`, `url`, `select`, `integer`, and `date`) also support filtering using additional lookup expressions. This allows for negation and other context-specific filtering.

These lookup expressions can be applied by adding a suffix to the desired field's name, e.g. `mac_address__n`. In this case, the filter expression is for negation and it is separated by two underscores. Below are the lookup expressions that are supported across different field types.

### Nullable Fields

+++ 2.1.0

Filters corresponding to nullable model fields (that is, `null=True`) of any type support the lookup expression:

- `__isnull` - field has a null value (_not_ blank -- a string-based (char) field with value `""` will match `__isnull=False`, _not_ `__isnull=True`)

### Numeric and Date/Time Fields

Numeric-based fields (ASN, VLAN ID, etc.) as well as date/time fields (`created`, `last_updated`, etc.) support these lookup expressions:

- `__n` - not equal to (negation)
- `__lt` - less than
- `__lte` - less than or equal
- `__gt` - greater than
- `__gte` - greater than or equal
- `__isnull` - is null (only if this field is nullable, which most numeric fields in Nautobot are not)

+++ 2.1.0 "Added `__isnull` support"

### String Fields

String-based (char) fields (Name, Address, etc.) support these lookup expressions:

- `__n` - not equal to (negation)
- `__ic` - case-insensitive contains
- `__nic` - negated case-insensitive contains
- `__isw` - case-insensitive starts-with
- `__nisw` - negated case-insensitive starts-with
- `__iew` - case-insensitive ends-with
- `__niew` - negated case-insensitive ends-with
- `__ie` - case-insensitive exact match
- `__nie` - negated case-insensitive exact match
- `__re` - case-sensitive regular expression match
- `__nre` - negated case-sensitive regular expression match
- `__ire` - case-insensitive regular expression match
- `__nire` - negated case-insensitive regular expression match
- `__isnull` - is null (only if this field is nullable, which most string fields in Nautobot are not)

+++ 2.1.0 "Added `__isnull` lookup expression"

### Foreign Keys & Other Fields

Certain other fields, namely foreign key relationships support the lookup expression:

- `__n` - not equal to (negation)
- `__isnull` - is null, only if this field is nullable

+++ 2.1.0 "Added `__isnull` lookup expression"

### IPAM Custom Filters

IPAM Custom Filters are related to the lookups defined in [Queryset Docs](../../../development/apps/api/models/queryset.md#ipam-custom-lookups). These lookups are mapped to the filters on Prefix's with minor modifications such as accounting for bad networks or stripping whitespace.

| Filter Name             | Lookup                           |
| ----------------------- | -------------------------------- |
| `address` (IP)          | `net_in`                         |
| `prefix`                | `net_equals()`                   |
| `prefix_exact`          | `net_equals()`                   |
| `within`                | `net_contained()`                |
| `within_include`        | `net_contained_or_equal()`       |
| `contains` (CIDR input) | `net_contains_or_equals()`       |
| `contains` (host input) | Custom logic for host input      |

!!! tip
    The `prefix` matches does not consider where host bits are set, matching how `netaddr`, `ipaddress`, and many popular subnet calculators do. If you want to consider the host bits, you should use `prefix_exact`.

    For example:

    - `prefix=10.32.0.34/28` **matches** `10.32.0.32/28`
    - `prefix_exact=10.32.0.34/28` **returns no results**

    This is useful when consumers need strict, unambiguous matching and want to avoid implicit normalization by the filtering layer.
