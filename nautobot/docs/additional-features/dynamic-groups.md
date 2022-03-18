# Dynamic Groups

EA Dynamic Group provides a way to organize objects of the same Content Type by matching filters. The Dynamic Group can be used to create unique groups of objects matching a given filter, such as Devices for a specific site location or set of locations. As indicated by the name, Dynamic Groups update in real time as objects are created, updated, or deleted.

When creating a Dynamic Group, one must select a Content Type to which it is associated, for example `dcim.device`. The filtering parameters saved to the group behave as a bi-directional search query that used to identify members of that group, and can also be used to determine from an individual object in which Dynamic Groups it is a member.

Once created the Content Type for a Dynamic Group may not be modified as this relationship is tightly-coupled to the available filtering parameters. All other fields may be updated at any time.

## Creating Dynamic Groups

Dynamic Groups can be created through the UI under Organization > Dynamic Groups and clicking the "Add" button, or through the REST API.

Each Dynamic Group must have a **name** which should be a simple database-friendly string, e.g. `device-site-ams01` and a **slug**. By default, the slug will be automatically generated from the name, however you may customize it if you like. You may also assign a corresponding human-friendly **description** (e.g. "Devices in site AMS01"). Finally, you must select a **content type** for the group that determines the filtering parameters available include objects as member into the group.

!!! note
    The content type of a Dynamic Group cannot be modified once created, so take care in selecting this initially. This helps to reduce the possibility of inconsistent data and enforces the importance of thinking about the network data model when defining a new Dynamic Group.

## Working with Dynamic Groups

Dynamic Groups can be accessed from the primary Dynamic Groups landing page in the web interface under the Organization > Dynamic Groups menu. From there you may view the list of available groups, search or filter the list, edit or, bulk delete groups. Additionally if a group's filter has matching members, the number of members may be clicked to take you to a filtered list view of those objects. Dynamic Groups cannot be imported nor can they be updated in bulk, as these operations would be complex and do not make sense in most cases.

From an individual object's detail page, if it is a member of any groups, a "Dynamic Groups" tab will display in the navigation tabs. Clicking that tab will display all Dynamic Groups of which this object is a member.

## Dynamic Groups and the REST API

Dynamic Groups are fairly straightforward however it i	s important to note that the `filter` field is a JSON field and it must be able to be used as valid query parameters for filtering objects of the corresponding content type.

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

It is an error to provide any value other than a JSON object (`{}` or a Python dictionary) for this field. Additionally, most filter fields accept multiple values and must be represented as a JSON array (Python list). Certain fields take Boolean values (`true`/`false`) or single numeric integers or character strings.

For example, consider this filter:

```json
{
  "interfaces": true,
  "name": "ams01-edge-01"
}
```

This would result in a Dynamic Group of a single Device with name "ams01-edge-01" if-and-only-if that device also has interfaces. While this likely wouldn't be all that useful of a filter for a Dynamic Group in practice, it illustrates that some fields take only one value instead of an array of values. It also underscores how important it is to think deliberately about defining your filter criteria.

### Filter Field Internals 

The filter fields are backed and validated by underlying filtersets (for example `nautobot.dcim.filters.DeviceFilterSet`) and are represented in the web interface as a dynamically-generated filter form that corresponds to each eligible filter field. Any invalid field names that are not eligible for filtering objects will be discarded upon validation. Any invalid field values will result in a validation error.

