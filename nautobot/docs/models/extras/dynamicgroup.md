# Dynamic Groups

A Dynamic Group provides a way to organize objects of the same Content Type by matching filters. The Dynamic Group can be used to create unique groups of objects matching a given filter, such as Devices for a specific site location or set of locations. As indicated by the name, Dynamic Groups update in real time as member objects are created, updated, or deleted.

When creating a Dynamic Group, one must select a Content Type to which it is associated, for example `dcim.device`. The filtering parameters saved to the group behave as a bi-directional search query that used to identify members of that group, and can also be used to determine from an individual object the list of Dynamic Groups to which it belongs.

Once created the Content Type for a Dynamic Group may not be modified as this relationship is tightly-coupled to the available filtering parameters. All other fields may be updated at any time.

## Basic Filtering

Dynamic Groups filtering is powered by **FilterSet** objects underneath the hood. Basic filtering is performed using the `filter` that is defined on a given Dynamic Group.

An object is considered to be a member of a Dynamic Group if it is of the same Content Type and it is not excluded by way of any of the filter critera specified for that group. By default, if a group has an empty filter (`{}`) it will include all objects of the matching Content Type, just as a defaut list view of objects would prior to any filter fields being filled in the web UI.

For example, for a Dynamic Group with Content Type of `dcim.device` and an empty filter, the list of members would be equivalent to the queryset for `Device.objects.all()`.

!!! warning
    This behavior was changed in v1.4.0. In v1.3.0 the default for a group with an empty filter was to fail "closed" and have zero members. As of v1.4.0, this behavior has been inverted to include all objects matching the content type by default instead of matching no objects. This was necessary to implement the progressive layering of child filters similarly to how we use filters to reduce desired objects from basic list view filters. This will described in more detail below.

The Dynamic Group edit view has a **Filter Fields** tab that allows one to specify filter criteria. The filter fields available for a given Content Type are backed and validated by underlying filterset classes (for example `nautobot.dcim.filters.DeviceFilterSet`) and are represented in the web interface as a dynamically-generated filter form that corresponds to each eligible filter field.

Any invalid field names that are not eligible for filtering objects will be discarded upon validation. Any invalid field values will result in a validation error.

## Advanced Filtering

<!-- markdownlint-disable MD036 -->
_Added in version 1.4.0_
<!-- markdownlint-enable MD036 -->

Advanced filtering is performed using nested Dynamic Group memberships.

An object is considered a member of an advanced Dynamic Group if it matches the aggregated filter criteria across all descendant groups.

The Dynamic Group edit view has a **Child Groups** tab that allows one to make other Dynamic Groups of the same content type children of the parent group.

!!! important
    Filter fields and child groups are mutually exclusive. A group may have either a filter defined, or child groups, but not both.

### Filter Generation

Descendant filters are always processed from the top down (or from left to right) starting with the parent group and ending with the last nested child group.

The nesting of Dynamic Group is performed using two advanced patterns: Set and graphs. Rules for each child group are processed using a set `operator`, and groups are sorted hierarchically as a directed acyclic graph (DAG), where the `weight` is used for sorting child groups topologically.

In both cases, the ordering of the tree of descendants from a parent group to its nested children is significant and critically important to how each subsequent filter or group of filters are processed to result in a final set of member objects.

Consider an example where there is a graph from the parent group to three direct child groups, the third of which has its own nested child group:

```no-highlight
parent
- first-child
- second-child
- third-child
  - nested-child
```

The filter generation would walk the graph topologically, starting from the base filter of `parent`, the filter of `first-child` would be applied to that of `parent`, then `second-child`, in order, all the way down. In the case of `third-child`, all of its children (only `nested-child` in this case) would be processed in order in the same way and the resultant filter from all of the child groups for `third-child` would be used to process the filter that resulted from the filter of `second-child`.

If this is confusing, don't worry. We'll cover it more in hands-on examples after this section.

### Weights

Weights are used to enforce the topological sorting of how filters are processed when traversing from a parent to each descending child group. Because this ordering is significant, care must be taken when constructing nested Dynamic Groups to result in filter parameters that have the desired outcome.

In practice, weights are automatically assigned in increments of `10`. In the web UI, child groups may be dragged and dropped to explicitly sort them.

Using the example group hierarchy above, the weights would be as follows:

```no-highlight
parent
- first-child {weight: 10}
- second-child {weight: 20}
- third-child {weight: 30}
  - nested-child {weight: 10}
```

### Operators

Set theory is applied when a new group is added as a child group. Three key concepts are at play: Intersections, Unions, and Differences.
Any filters provided by the child groups are used to filter the members from the parent group using one of three operators: **Restrict (AND)**, **Include (OR)**, or **Exclude (NOT)**. This allows for logical parenthetical grouping of nested groups by the operator you choose for that child group association to the parent.

We have attempted to simplify working with these operators by giving them both human-readable and Boolean name mappings. They are as follows:

- **Restrict (Boolean `AND`)** - The **Restrict** operator performs a set _intersection_ on the queryset, and is equivalent to a Boolean `AND`. Any objects matching the child filter are _restricted_ (aka _intersected_) with the preceding filter. All filter criteria must match between the filters for a member object to be included in the resultant filter.
- **Include (Boolean `OR`)** - The **Include** operator performs a set _union_ on the queryset, and is equivalent to a Boolean `OR`. Any objects matching the child filter are _included_ (aka _unioned_) with the preceding filter. Any filter criteria may match between the filters for member objects to be included in the resultant filter.
- **Exclude (Boolean `NOT`)** - The **Exclude** operator performs a set _difference_ on the queryset, and is equivalent to a Boolean `NOT`. Any objects matching the child filter are _excluded_ (aka _differenced_) from the preceding filter. Any matching objects from the child filter will be negated from the members of the resultant filter.

Using the example group hiearchy from above, let's apply operators and explain how it would work:

```no-highlight
parent
- first-child {weight: 10, operator: intersection}
- second-child {weight: 20, operator: union}
- third-child {weight: 30, operator: difference}
  - nested-child {weight: 10, operator: intersection}
```

## Creating Dynamic Groups

Dynamic Groups can be created through the UI under _Organization > Dynamic Groups_ and clicking the "Add" button, or through the REST API.

Each Dynamic Group must have a human-readable **Name** string, e.g. `device-site-ams01` and a **Slug**, which should be a simple database-friendly string. By default, the slug will be automatically generated from the name, however you may customize it if you like. You may also assign a corresponding human-friendly **Description** (e.g. "Devices in site AMS01"). Finally, you must select a **Content Type** for the group that determines the filtering parameters available include objects as member into the group.

Once a new Dynamic Group is created, the **Filter Fields** or **Child Groups** may be specified.

!!! note
    The content type of a Dynamic Group cannot be modified once created, so take care in selecting this initially. This helps to reduce the possibility of inconsistent data and enforces the importance of thinking about the network data model when defining a new Dynamic Group.

### Working with Dynamic Groups

Dynamic Groups can be accessed from the primary Dynamic Groups landing page in the web interface under the _Organization > Dynamic Groups_ menu. From there you may view the list of available groups, search or filter the list, view or edit an individual group, or bulk delete groups. Additionally if a group's filter has matching members, the number of members may be clicked to take you to a filtered list view of those objects.

Dynamic Groups cannot be imported nor can they be updated in bulk, as these operations would be complex and do not make sense in most cases.

From an individual object's detail page, if it is a member of any groups, a "Dynamic Groups" tab will display in the navigation tabs. Clicking that tab will display all Dynamic Groups of which this object is a member.

## Dynamic Groups and the REST API

Dynamic Groups are fully supported by the API.

### Specifying Filter Conditions

Dynamic Groups are fairly straightforward however it is important to note that the `filter` field is a JSON field and it must be able to be used as valid query parameters for filtering objects of the corresponding content type.

Consider, for example, the following Dynamic Group:

```json
{
    "id": "9664758b-9de1-4b2b-87c2-8be40aa2238d",
    "url": "http://localhost:6789/api/extras/dynamic-groups/9664758b-9de1-4b2b-87c2-8be40aa2238d/",
    "name": "devices-a-star",
    "slug": "devices-a-star",
    "description": "Devices in sites starting with 'A'",
    "content_type": "dcim.device",
    "filter": {
        "site": [
            "ams01",
            "ang01",
            "atl01",
            "atl02",
            "azd01"
        ]
    },
    "display": "devices-a-star"
}
```

It is an error to provide any value other than a JSON object (`{}` or a Python dictionary) for the `filter` field. Additionally, most fields within the `filter` accept multiple values and must be represented as a JSON array (Python list). Certain fields take Boolean values (JSON `true`/`false`) or single numeric integers or character strings.

For example, consider this filter:

```json
{
  "has_interfaces": true,
  "name": "ams01-edge-01"
}
```

This would result in a Dynamic Group of a single Device with name "ams01-edge-01" if-and-only-if that device also has interfaces. While this likely wouldn't be all that useful of a filter for a Dynamic Group in practice, it illustrates that some fields take only one value instead of an array of values. It also underscores how important it is to think deliberately about defining your filter criteria.

!!! note
  Please refer to either the source code definition of the `{model_name}FilterSet` (e.g. for `Device` it would be `nautobot.dcim.filters.DeviceFilterSet`) or the API documentation for the list endpoint (e.g. `/api/dcim/devices/`) for a given model object, to view the available filter fields and their expectations.

### Adding Child Groups

NYI
