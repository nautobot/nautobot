# VLAN Groups

VLAN groups can be used to organize VLANs within Nautobot. Each group may optionally be assigned to a specific location, but a group cannot belong to multiple locations.

Groups can also be used to enforce uniqueness: Each VLAN within a group must have a unique ID and name. VLANs which are not assigned to a group may have overlapping names and IDs (including VLANs which belong to a common location). For example, you can create two VLANs with ID 123, but they cannot both be assigned to the same group.

## VLAN Group Ranges

+++ 2.3.6

VLAN Groups contain a mandatory `range` field with a default value of `1-4094` (permitting all VLANs). This field may be used to constrain the valid member VLANs of the group. VLANs can only be associated with a given VLAN Group if their VLAN identifiers ("VIDs") fall within the specified `range`.
Range value accepts commas and dashes, with examples as follows:

* 1
* 1-5
* 1-5,10
* 1-5,10-15
* 1-5,10-15,16,17,18,19,20

Values between dashes will also be expanded into a list of VLANs.

## Creating new VLANs in a VLANGroup programatically

+++ 2.3.6

VLAN Groups offer an API endpoint to list available VIDs and create new VLANs programmatically:

`/api/ipam/vlan-groups/<vlan_group_id>/available-vlans/`

A `GET` request to this API endpoint will return a list of all available (unassigned) VIDs available in the given `VLANGroup`.

A `POST` request to the same API endpoint will create `VLAN` record(s) in the given `VLANGroup`. Note that you must specify the `name` and `status` of each VLAN to be created as a part of this request, but the `vlan_group` and `vid` may be omitted as they can be automatically assigned by this API. See below.

### Creating VLANGroup example

To create a new `VLANGroup` with a `range` field of: `5-10` (permit VLANs `5, 6, 7, 8, 9, 10`), issue following POST request:

```no-highlight
curl -X POST -H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.0; indent=4" \
http://nautobot/api/ipam/vlan-groups/ \
--data '[{"name": "Enterprise VLANs", "range": "5-10"}]'
```

`VLANGroup` was created as follows:

```json
[
    {
        "id": "c16d5d1d-40d6-4902-b89d-6294e60cb4bf",
        "object_type": "ipam.vlangroup",
        "display": "Enterprise VLANs",
        "url": "http://nautobot/api/ipam/vlan-groups/c16d5d1d-40d6-4902-b89d-6294e60cb4bf/",
        "natural_slug": "enterprise-vlans_c16d",
        "name": "Enterprise VLANs",
        "description": "",
        "range": "5-10",
        "location": null,
        "created": "2024-09-25T09:27:16.343655Z",
        "last_updated": "2024-09-25T09:27:16.343670Z",
        "notes_url": "http://nautobot/api/ipam/vlan-groups/c16d5d1d-40d6-4902-b89d-6294e60cb4bf/notes/",
        "custom_fields": {},
        "computed_fields": {},
        "relationships": {}
    }
]
```

### Listing available VLANs example

Then, to list all available VLAN IDs within the just-created `VLANGroup`, issue a GET request:

```no-highlight
curl -X GET -H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.0; indent=4" \
http://nautobot/api/ipam/vlan-groups/c16d5d1d-40d6-4902-b89d-6294e60cb4bf/available-vlans/
```

```json
{
    "count": 6,
    "next": null,
    "previous": null,
    "results": [
        5,
        6,
        7,
        8,
        9,
        10
    ]
}
```

### Creating new VLANs example

The `/api/ipam/vlan-groups/<vlan_group_id>/available-vlans/` API endpoint accepts `POST` requests to create a new VLAN record, similar to the `/api/ipam/vlans/` API endpoint. However, there are some characteristic differences in the behavior of `/available-vlans/` with regard to its input and output:

* Accepts a single dictionary as input to create 1 VLAN, in which case it returns a single dictionary describing the created VLAN
* Accepts a list of dictionaries as input to create one or more VLANs, in which case it returns a list of VLAN objects
* The fields `name` and `status` of are mandatory inputs for each VLAN to be created
* The field `vid` is optional and might be specified to override auto-allocation for a given VLAN
    * Will not accept a request with the same `vid` value specified multiple times
* Will not accept a `vlan_group` attribute different than that already specified in the request's URL
* Other `VLAN` model fields are permitted and optional
* As with the `/vlans/` endpoint, specifying `locations` in the POST request is not presently supported; you can make a subsequent call(s) to the `/api/ipam/vlan-location-assignments/` endpoint to update the many-to-many association between the created VLAN(s) and desired Location(s)

To create two new VLANs, a data payload has to be specified. In the case of the first VLAN, its `VLAN ID` will be automatically determined based on `VLANGroups` availability, in the case of the second VLAN we explicitly request `vid` 8:

```no-highlight
curl -X POST -H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.0; indent=4" \
http://nautobot/api/ipam/vlan-groups/c16d5d1d-40d6-4902-b89d-6294e60cb4bf/available-vlans/ \
--data '[
{"name": "First VLAN", "status": "1e560c4d-07ef-4d49-af6e-c85aa1f295d3"},
{"name": "Second VLAN", "vid": 8, "status": "1e560c4d-07ef-4d49-af6e-c85aa1f295d3"}
]'
```

`VLANs` created:

```json
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": "58bd2a10-33f7-45e2-93d2-f56be25dfe8c",
            "object_type": "ipam.vlan",
            "display": "First VLAN (5)",
            "url": "http://nautobot/api/ipam/vlans/58bd2a10-33f7-45e2-93d2-f56be25dfe8c/",
            "natural_slug": "58bd2a10-33f7-45e2-93d2-f56be25dfe8c_58bd",
            "vid": 5,
            "name": "First VLAN",
            "description": "",
            "vlan_group": {
                "id": "c16d5d1d-40d6-4902-b89d-6294e60cb4bf",
                "object_type": "ipam.vlangroup",
                "url": "http://nautobot/api/ipam/vlan-groups/c16d5d1d-40d6-4902-b89d-6294e60cb4bf/"
            },
            "status": {
                "id": "1e560c4d-07ef-4d49-af6e-c85aa1f295d3",
                "object_type": "extras.status",
                "url": "http://nautobot/api/extras/statuses/1e560c4d-07ef-4d49-af6e-c85aa1f295d3/"
            },
            "role": null,
            "tenant": null,
            "locations": [],
            "created": "2024-09-25T09:36:07.587950Z",
            "last_updated": "2024-09-25T09:36:07.587963Z",
            "tags": [],
            "notes_url": "http://nautobot/api/ipam/vlans/58bd2a10-33f7-45e2-93d2-f56be25dfe8c/notes/",
            "custom_fields": {},
            "computed_fields": {},
            "relationships": {}
        },
        {
            "id": "9b7c6b03-9140-4b00-940f-5dbcde173de1",
            "object_type": "ipam.vlan",
            "display": "Second VLAN (8)",
            "url": "http://nautobot/api/ipam/vlans/9b7c6b03-9140-4b00-940f-5dbcde173de1/",
            "natural_slug": "9b7c6b03-9140-4b00-940f-5dbcde173de1_9b7c",
            "vid": 8,
            "name": "Second VLAN",
            "description": "",
            "vlan_group": {
                "id": "c16d5d1d-40d6-4902-b89d-6294e60cb4bf",
                "object_type": "ipam.vlangroup",
                "url": "http://nautobot/api/ipam/vlan-groups/c16d5d1d-40d6-4902-b89d-6294e60cb4bf/"
            },
            "status": {
                "id": "1e560c4d-07ef-4d49-af6e-c85aa1f295d3",
                "object_type": "extras.status",
                "url": "http://nautobot/api/extras/statuses/1e560c4d-07ef-4d49-af6e-c85aa1f295d3/"
            },
            "role": null,
            "tenant": null,
            "locations": [],
            "created": "2024-09-25T09:36:07.634563Z",
            "last_updated": "2024-09-25T09:36:07.634578Z",
            "tags": [],
            "notes_url": "http://nautobot/api/ipam/vlans/9b7c6b03-9140-4b00-940f-5dbcde173de1/notes/",
            "custom_fields": {},
            "computed_fields": {},
            "relationships": {}
        }
    ]
}
```
