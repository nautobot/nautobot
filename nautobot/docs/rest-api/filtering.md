# REST API Filtering

## Filtering Objects

The objects returned by an API list endpoint can be filtered by attaching one or more query parameters to the request URL. For example, `GET /api/dcim/sites/?status=active` will return only sites with a status of "active."

Multiple parameters can be joined to further narrow results. For example, `GET /api/dcim/sites/?status=active&region=europe` will return only active sites within the Europe region.

Generally, passing multiple values for a single parameter will result in a logical OR operation. For example, `GET /api/dcim/sites/?region=north-america&region=south-america` will return sites in North America _or_ South America. However, a logical AND operation will be used in instances where a field may have multiple values, such as tags. For example, `GET /api/dcim/sites/?tag=foo&tag=bar` will return only sites which have both the "foo" _and_ "bar" tags applied.

### Filtering by Choice Field

Some models have fields which are limited to specific choices, such as the `status` field on the Prefix model. To find all available choices for this field, make an authenticated `OPTIONS` request to the model's list endpoint, and use `jq` to extract the relevant parameters:

```no-highlight
$ curl -s -X OPTIONS \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
http://nautobot/api/ipam/prefixes/ | jq ".actions.POST.status.choices"
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

Custom fields can be mixed with built-in fields to further narrow results. When creating a custom string field, the type of filtering selected (loose versus exact) determines whether partial or full matching is used.

## Lookup Expressions

Certain model fields also support filtering using additional lookup expressions. This allows
for negation and other context-specific filtering.

These lookup expressions can be applied by adding a suffix to the desired field's name, e.g. `mac_address__n`. In this case, the filter expression is for negation and it is separated by two underscores. Below are the lookup expressions that are supported across different field types.

### Numeric Fields

Numeric based fields (ASN, VLAN ID, etc) support these lookup expressions:

- `n` - not equal to (negation)
- `lt` - less than
- `lte` - less than or equal
- `gt` - greater than
- `gte` - greater than or equal

### String Fields

String based (char) fields (Name, Address, etc) support these lookup expressions:

- `n` - not equal to (negation)
- `ic` - case insensitive contains
- `nic` - negated case insensitive contains
- `isw` - case insensitive starts with
- `nisw` - negated case insensitive starts with
- `iew` - case insensitive ends with
- `niew` - negated case insensitive ends with
- `ie` - case insensitive exact match
- `nie` - negated case insensitive exact match

### Foreign Keys & Other Fields

Certain other fields, namely foreign key relationships support just the negation
expression: `n`.
