# QuerySet

A **QuerySet** is a core Django concept representing a collection of database queries built from a model. QuerySets are constructed using the model's manager (e.g., `Device.objects`) and provide methods such as `.filter()`, `.exclude()`, and `.order_by()` to build up queries. QuerySets are evaluated lazily, meaning the actual database query is not executed until the data is needed.

Example:
```python
Device.objects.filter(location__name="AMS01").filter(manufacturer__name="Cisco")
```

QuerySets are tightly coupled to the model's fields and relationships, and are responsible for translating Python code into SQL queries.

## QuerySets vs. FilterSets

There is often confusion between QuerySets and FilterSets, as both are used to retrieve and manipulate data in Django, but they serve different purposes and operate at different layers.

A **FilterSet** is a concept provided by the [django-filter](https://django-filter.readthedocs.io/) library, which is used extensively in Nautobot. FilterSets define a set of filters that can be applied to a QuerySet, typically based on user input (such as query parameters in an API request). FilterSets allow for more complex and user-friendly filtering logic, including support for custom fields, lookup expressions, and validation.

FilterSets are not a replacement for QuerySets; rather, they operate on top of QuerySets. When an API endpoint receives filter parameters, a FilterSet processes those parameters and applies the corresponding filters to the underlying QuerySet.

!!! tip
    One concept to consider is that QuerySet's have `.filter()` and `.exclude()` methods, while a FilterSet will have a `__ic` and `__nic` param to allow you in a single API call articulate what would take multiple methods in a QuerySet.

Example:
```python
class DeviceFilterSet(
    NautobotFilterSet,
):
    manufacturer = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device_type__manufacturer",
        queryset=Manufacturer.objects.all(),
        to_field_name="name",
        label="Manufacturer (name or ID)",
    )

# Usage
filtered_qs = DeviceFilter({'manufacturer': 'Cisco'}, queryset=Device.objects.all()).qs
```

- **QuerySet**: Represents a database query built from a model; provides methods to construct and execute queries.
- **FilterSet**: Defines a set of filters (often for user input) and applies them to a QuerySet; enables advanced filtering logic and validation.

In Nautobot, FilterSets are used to expose flexible and powerful filtering capabilities in the REST API, while QuerySets remain the foundation for all database queries.

To provide concrete examples, note that these queryset's and FiltersSets result in the same queryset.


```
>>> Device.objects.filter(device_type__manufacturer__name='Cisco')
>>> DeviceFilterSet({'manufacturer': 'Cisco'}, queryset=Device.objects.all()).qs
```

You can see how the `device_type__manufacturer__name` became simply `manufacturer` in the filterset, since that was created.

```
>>> Device.objects.filter(name__icontains='ams01')
>>> DeviceFilterSet({'name__ic': 'ams01'}, queryset=Device.objects.all()).qs
```

You can see how the `icontains` becomes `ic`, as there is dynamically applied filters applied to each FilterSet. 

So while often the QuerySet and FilterSet attributes will be the same, there is no guarantee, so you must refer to the appropriate documentation when working with either a QuerySet or a FilterSet.

## RestrictedQuerySet

Nautobot provides the ability to include attribute based access control (ABAC) via the method of `RestrictedQuerySet`. That is to say that any model in Nautobot that intends to have permissions applied, should should have the `Model.objects` object manager inherit from Nautobot. 

## IPAM Custom Lookups

There are [Custom Lookups](https://docs.djangoproject.com/en/3.2/howto/custom-lookups/) built for the `VarbinaryIPField` field types. While the `VarbinaryIPField` is applied to fields for `network`, `host`, and `broadcast`, the below filters only apply to `network` and `host`. The design makes an assumption that there is in fact a `broadcast` (of type `VarbinaryIPField`) and `prefix_length` (of type `Integer`) within the same model. This assumption is used to understand the relevant scope of the network in question and is important to note when extending the Nautobot core or App data model.

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
