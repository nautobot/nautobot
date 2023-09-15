# REST API Overview

## What is a REST API?

REST stands for [representational state transfer](https://en.wikipedia.org/wiki/Representational_state_transfer). It's a particular type of API which employs HTTP requests and [JavaScript Object Notation (JSON)](https://www.json.org/) to facilitate create, retrieve, update, and delete (CRUD) operations on objects within an application. Each type of operation is associated with a particular HTTP verb:

* `GET`: Retrieve an object or list of objects
* `POST`: Create an object
* `PUT` / `PATCH`: Modify an existing object. `PUT` requires all mandatory fields to be specified, while `PATCH` only expects the field that is being modified to be specified.
* `DELETE`: Delete an existing object

Additionally, the `OPTIONS` verb can be used to inspect a particular REST API endpoint and return all supported actions and their available parameters.

One of the primary benefits of a REST API is its human-friendliness. Because it utilizes HTTP and JSON, it's very easy to interact with Nautobot data on the command line using common tools. For example, we can request an IP address from Nautobot and output the JSON using `curl` and `jq`. The following command makes an HTTP `GET` request for information about a particular IP address, identified by its primary key, and uses `jq` to present the raw JSON data returned in a more human-friendly format. (Piping the output through `jq` isn't strictly required but makes it much easier to read.)

```no-highlight
curl -s http://nautobot/api/ipam/ip-addresses/83445aa3-bbd3-4ab4-86f5-36942ce9df60/ | jq '.'
```

```json
{
  "id": "83445aa3-bbd3-4ab4-86f5-36942ce9df60",
  "url": "http://nautobot/api/ipam/ip-addresses/83445aa3-bbd3-4ab4-86f5-36942ce9df60/",
  "display": "10.0.60.39/32",
  "custom_fields": {},
  "notes_url": "http://nautobot/api/ipam/ip-addresses/83445aa3-bbd3-4ab4-86f5-36942ce9df60/notes/",
  "family": {
    "value": 4,
    "label": "IPv4"
  },
  "address": "10.0.60.39/32",
  "nat_outside_list": [
    {
        "id": "a7569104-ed58-4938-ab6f-cb6a9e584f14",
        "object_type": "ipam.ipaddress",
        "url": "http://nautobot/api/ipam/ip-addresses/a7569104-ed58-4938-ab6f-cb6a9e584f14/"
    }
  ],
  "created": "2023-04-25T12:46:09.152507Z",
  "last_updated": "2023-04-25T12:46:09.163545Z",
  "host": "10.0.60.39",
  "mask_length": 32,
  "dns_name": "desktop-08.cook.biz",
  "description": "This is an IP Address",
  "role": {
    "id": "e7a815b0-2c48-499a-84b8-f20350abe415",
    "object_type": "extras.role",
    "url": "http://nautobot/api/extras/roles/e7a815b0-2c48-499a-84b8-f20350abe415/",
  },
  "status": {
    "id": "b7f6a447-5616-4533-a6d5-a4ece50cd08c",
    "object_type": "extras.status",
    "url": "http://nautobot/api/extras/statuses/b7f6a447-5616-4533-a6d5-a4ece50cd08c/",
  },
  "vrf": null,
  "tenant": {
    "id": "501fffe7-5302-40ae-b9e4-27d5e3ff2108",
    "object_type": "tenancy.tenant",
    "url": "http://nautobot/api/tenancy/tenants/501fffe7-5302-40ae-b9e4-27d5e3ff2108/",
  },
  "nat_inside": null,
  "tags": []
}
```

Each attribute of the IP address is expressed as an attribute of the JSON object. Related objects are identified by their own URLs that may be accessed to retrieve more details of the related object, as in the case of the `role` and `status` fields above. Every object includes a primary key named `id` which uniquely identifies it in the database.

## Interactive Documentation

Comprehensive, interactive documentation of all REST API endpoints is available on a running Nautobot instance at `/api/docs/`. This interface provides a convenient sandbox for researching and experimenting with specific endpoints and request types. The API itself can also be explored using a web browser by navigating to its root at `/api/`.

+++ 1.3.0
    You can view or explore a specific REST API [version](#versioning) by adding the API version as a query parameter, for example `/api/docs/?api_version=2.0` or `/api/?api_version=2.0`

## Endpoint Hierarchy

Nautobot's entire REST API is housed under the API root at `https://<hostname>/api/`. The URL structure is divided at the root level by application: circuits, DCIM, extras, IPAM, plugins, tenancy, users, and virtualization. Within each application exists a separate path for each model. For example, the provider and circuit objects are located under the "circuits" application:

* `/api/circuits/providers/`
* `/api/circuits/circuits/`

Likewise, the location, rack, and device objects are located under the "DCIM" application:

* `/api/dcim/locations/`
* `/api/dcim/racks/`
* `/api/dcim/devices/`

The full hierarchy of available endpoints can be viewed by navigating to the API root in a web browser.

Each model generally has two views associated with it: a list view and a detail view. The list view is used to retrieve a list of multiple objects and to create new objects. The detail view is used to retrieve, update, or delete an single existing object. All objects are referenced by their UUID primary key (`id`).

* `/api/dcim/devices/` - List existing devices or create a new device
* `/api/dcim/devices/6a522ebb-5739-4c5c-922f-ab4a2dc12eb0/` - Retrieve, update, or delete the device with ID 6a522ebb-5739-4c5c-922f-ab4a2dc12eb0

Lists of objects can be filtered using a set of query parameters. For example, to find all interfaces belonging to the device with ID 6a522ebb-5739-4c5c-922f-ab4a2dc12eb0:

```no-highlight
GET /api/dcim/interfaces/?device=6a522ebb-5739-4c5c-922f-ab4a2dc12eb0
```

See the [filtering documentation](filtering.md) for more details.

## Versioning

+++ 1.3.0

As of Nautobot 1.3, the REST API supports multiple versions. A REST API client may request a given API version by including a `major.minor` Nautobot version number in its request in one of two ways:

1. A client may include a `version` in its HTTP Accept header, for example `Accept: application/json; version=2.0`
2. A client may include an `api_version` as a URL query parameter, for example `/api/extras/jobs/?api_version=2.0`

Generally the former approach is recommended when writing automated API integrations, as it can be set as a general request header alongside the [authentication token](authentication.md) and re-used across a series of REST API interactions, while the latter approach may be more convenient when initially exploring the REST API via the interactive documentation as described above.

### Default Versions

By default, a REST API request that does not specify an API version number will default to compatibility with the current Nautobot version.

+++ 1.3.0
    For Nautobot 1.x, the default API behavior is to be compatible with the REST API of Nautobot version 1.2, in other words, for all Nautobot 1.x versions (beginning with Nautobot 1.2.0), `Accept: application/json` is functionally equivalent to `Accept: application/json; version=1.2`.

+/- 2.0.0
    As of Nautobot 2.0, the default API behavior is changed to use the latest available REST API version. In other words, the default REST API version for Nautobot 2.0.y will be `2.0`, for Nautobot 2.1.y will be `2.1`, etc. This means that REST API clients that do not explicitly request a particular REST API version may encounter potentially [breaking changes](#breaking-changes) in the REST API when Nautobot is upgraded to a new minor or major version.

!!! important
    As a best practice, it is recommended that a REST API client _should always_ request the exact Nautobot REST API version that it is compatible with, rather than relying on the default behavior to remain constant.

!!! tip
    Any successful REST API response will include an `API-Version` header showing the API version that is in use for the specific API request being handled.

### Non-Breaking Changes

Non-breaking (forward- and backward-compatible) REST API changes may be introduced in major or minor Nautobot releases. Since these changes are non-breaking, they will _not_ correspond to the introduction of a new API version, but will be added seamlessly to the existing API version, and so will immediately be available to existing REST API clients. Examples would include:

* Addition of new fields in GET responses
* Added support for new, _optional_ fields in POST/PUT/PATCH requests
* Deprecation (but not removal) of existing fields

!!! important
    There is no way to "opt out" of backwards-compatible enhancements to the REST API; because they are fully backwards-compatible there should never be a need to do so. Thus, for example, a client requesting API version `1.2` from a Nautobot 1.3 server may actually receive the (updated but still backwards-compatible) `1.3` API version as a response. For this reason, clients should always default to ignoring additional fields in an API response that they do not understand, rather than reporting an error.

### Breaking Changes

Breaking (non-backward-compatible) REST API changes also may be introduced in major or minor Nautobot releases. Examples would include:

* Removal of deprecated fields
* Addition of new, _required_ fields in POST/PUT/PATCH requests or changing an existing field from optional to required
* Changed field types (for example, changing a single value to a list of values)
* Redesigned API (for example, listing and accessing Job instances by UUID primary-key instead of by class-path string)

Per Nautobot's [feature-deprecation policy](../../../development/core/index.md#deprecation-policy), the previous REST API version(s) will continue to be supported until the next major release. Upon the next major release, previously deprecated API versions will be removed and the newest behavior will become the default. You will no longer be able to request API versions from the previous major version.

!!! important
    Again, REST API clients are strongly encouraged to always specify the REST API version they are expecting, as otherwise unexpected breaking changes may be encountered when Nautobot is upgraded to a new major or minor release.

### Example of API Version Behavior

As an example, let us say that Nautobot 2.1 introduced a new, _non-backwards-compatible_ REST API for the `/api/extras/jobs/` endpoint, and also introduced a new, _backwards-compatible_ set of additional fields on the `/api/dcim/locations/` endpoint. Depending on what API version a REST client interacting with Nautobot 2.1 specified (or didn't specify), it would see the following responses from the server:

| API endpoint        | Requested API version | Response                                        |
| ------------------- | --------------------- | ----------------------------------------------- |
| `/api/extras/jobs/` | (unspecified)         | Updated 2.1 REST API (not backwards compatible) |
| `/api/extras/jobs/` | `2.0`                 | Deprecated 2.0-compatible REST API              |
| `/api/extras/jobs/` | `2.1`                 | New/updated 2.1-compatible REST API             |

+/- 2.0.0
    The [default behavior](#default-versions) when the API version is unspecified is changed from Nautobot 1.x.

| API endpoint            | Requested API version | Response                                     |
| ----------------------- | --------------------- | -------------------------------------------- |
| `/api/dcim/locations/`  | (unspecified)         | 2.1-updated, 2.0-compatible REST API         |
| `/api/dcim/locations/`  | `2.0`                 | 2.1-updated, 2.0-compatible REST API         |
| `/api/dcim/locations/`  | `2.1`                 | 2.1-updated, 2.0-compatible REST API         |

| API endpoint        | Requested API version | Response                                     |
| ------------------- | --------------------- | -------------------------------------------- |
| `/api/dcim/racks/`  | (unspecified)         | 2.1-compatible REST API (unchanged from 2.0) |
| `/api/dcim/racks/`  | `2.0`                 | 2.1-compatible REST API (unchanged from 2.0) |
| `/api/dcim/racks/`  | `2.1`                 | 2.1-compatible REST API (unchanged from 2.0) |

### APISelect with versioning capability

+++ 1.3.0

The constructor for Nautobot's `APISelect`/`APISelectMultiple` UI widgets now includes an optional `api_version` argument which if set overrides the default API version of the request.

## Serialization

The REST API employs "serializers" to represent model data. The representation produced by a serializer typically includes all relevant database table fields which comprise the model, and may also include additional metadata such as information about other relevant objects in the database. Much like the database model itself, a serializer typically will represent information about "parent" objects (those objects that needed to exist in order to define the current object, such as `DeviceType` and `Location` for a `DeviceSerializer`) but typically will not include information about "child" objects (those objects that depend on the current object in order to be defined, such as `Interface` objects for a `DeviceSerializer`).

### Related Objects

Related objects (e.g. `ForeignKey` fields) are representable in several different ways. By default, when retrieving an object via the REST API, related objects are represented by URLs, or by a JSON `null` if no such related object exists. These URLs may be accessed in order to retrieve the full details of such related objects if needed/desired. For example, when retrieving an `IPAddress`, you might see:

```json
{
    "id": "83445aa3-bbd3-4ab4-86f5-36942ce9df60",
    "url": "http://localhost:8080/api/ipam/ip-addresses/83445aa3-bbd3-4ab4-86f5-36942ce9df60/",
    "display": "10.0.60.39/32",
    "address": "10.0.60.39/32",
    ...
    "role": {
        "id": "e7a815b0-2c48-499a-84b8-f20350abe415",
        "object_type": "extras.role",
        "url": "http://localhost:8080/api/extras/roles/e7a815b0-2c48-499a-84b8-f20350abe415/",
    },
    "status": {
        "id": "b7f6a447-5616-4533-a6d5-a4ece50cd08c",
        "object_type": "extras.status",
        "url": "http://localhost:8080/api/extras/statuses/b7f6a447-5616-4533-a6d5-a4ece50cd08c/",
    },
    "vrf": null,
    "tenant": {
        "id": "501fffe7-5302-40ae-b9e4-27d5e3ff2108",
        "object_type": "tenancy.tenant",
        "url": "http://localhost:8080/api/tenancy/tenants/501fffe7-5302-40ae-b9e4-27d5e3ff2108/",
    },
    "nat_inside": null,
    "tags": []
}
```

Here, the `role`, `status`, `vrf`, `tenant`, and `nat_outside` fields represent objects related to this `IPAddress`, and the `tags` field is a list of such objects (no tags in this example).

+/- 2.0.0
    The representation of related objects on retrieval has changed from Nautobot 1.x. The `brief` query parameter has been removed, and distinct "nested" serializers no longer exist. Instead, the `depth` parameter controls whether related objects are represented by URLs or as nested objects. Please see [Depth Query Parameter](#depth-query-parameter) for more details.

When performing write API actions (`POST`, `PUT`, and `PATCH`), related objects may be specified by either UUID (primary key), or by a set of attributes sufficiently unique to return the desired object, or by their [composite key](../../../development/core/natural-keys.md).

+++ 2.0.0
    Support for specifying a related object by composite-key was added.

For example, when creating a new device, its rack can be specified by Nautobot ID (PK):

```json
{
    "name": "MyNewDevice",
    "rack": "7f3ca431-8103-45cc-a9ce-b94c1f784a1d",
    ...
}
```

Or by a set of nested attributes which uniquely identify the rack:

```json
{
    "name": "MyNewDevice",
    "rack": {
        "location": {
            "name": "Equinix DC6"
        },
        "name": "R204"
    },
    ...
}
```

Or by the [composite key](../../../development/core/natural-keys.md) of the rack (for the Rack model, this is just its name, but this will vary by object type - you can always find this information under the Advanced tab of an object's detail view):

```json
{
    "name": "MyNewDevice",
    "rack": "R204",
    ...
}
```

Note that if the provided parameters do not match exactly one object, a validation error will be raised.

### Generic Relations

Some objects within Nautobot have attributes which can reference an object of multiple types, known as _generic relations_. For example, a `Cable` can be terminated (connected) to an `Interface`, or a `FrontPort`, or a `RearPort`, etc. For such generic relations, when making this assignment via the REST API, we must specify two attributes, typically an `object_type` and an `object_id`, and by convention in Nautobot's API:

* the `object_type` is the type of assigned object, typically represented as `<app_label>.<model_name>`
* the `object_id` is the UUID (primary key) of the assigned object.

For example, the two ends of a Cable are identified by `termination_a_type`/`termination_a_id` and `termination_b_type`/`termination_b_id`, and might be specified on creation as something like:

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.0; indent=4" \
http://nautobot/api/dcim/cables/ \
--data '{
    "termination_a_type": "dcim.interface",
    "termination_a_id": "96ee6c25-d689-46f4-b552-eb72977c27b8",
    "termination_b_type": "dcim.frontport",
    "termination_b_id": "ca54e2cc-d1b5-46e2-bb7d-85b1a9e3c1d0",
    ...
}'
```

On retrieval, the REST API will include the `object_type` and `object_id` fields, but will also typically for convenience include an `object` field containing the URL or nested details of the object identified by the type/id fields. For the above `Cable` example, the retrieval response might look something like:

```json
{
    "id": "549dae0d-3345-4bd1-8626-085e46a36ded",
    "url": "http://localhost:8080/api/dcim/cables/549dae0d-3345-4bd1-8626-085e46a36ded/",
    ...
    "termination_a_type": "dcim.interface",
    "termination_b_type": "dcim.frontport",
    "termination_a_id": "96ee6c25-d689-46f4-b552-eb72977c27b8",
    "termination_b_id": "ca54e2cc-d1b5-46e2-bb7d-85b1a9e3c1d0",
    "termination_a": "http://localhost:8080/api/dcim/interfaces/96ee6c25-d689-46f4-b552-eb72977c27b8/",
    "termination_b": "http://localhost:8080/api/dcim/front-ports/ca54e2cc-d1b5-46e2-bb7d-85b1a9e3c1d0/",
    ...
}
```

### Many-To-Many Relationships

+++ 2.0.0

Many-to-many relationships differ from one-to-many and one-to-one relationships because they utilize a separate database table called a "through table" to track the relationships instead of a single field in an existing table. In Nautobot 2.0, some relationships such as `IPAddress` to `Interface`/`VMInterface`, `Prefix` to `VRF`, and `VRF` to `Device`/`VirtualMachine` are represented as many-to-many relationships. The REST API represents these relationships as nested objects for retrieval, but in order to create, update or delete these relationships, the through table endpoint must be used. Currently, the only through table endpoint available is the [`IPAddress` to `Interface`/`VMInterface` at `/api/ipam/ip-address-to-interface/`](../../administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#new-interface-to-ip-address-relationship-endpoint).

## Pagination

API responses which contain a list of many objects will be paginated for efficiency. The root JSON object returned by a list endpoint contains the following attributes:

* `count`: The total number of all objects matching the query
* `next`: A hyperlink to the next page of results (if applicable)
* `previous`: A hyperlink to the previous page of results (if applicable)
* `results`: The list of objects on the current page

Here is an example of a paginated response:

```json
HTTP 200 OK
Allow: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
API-Version: 1.2
Content-Type: application/json
Vary: Accept

{
    "count": 2861,
    "next": "http://nautobot/api/dcim/devices/?limit=50&offset=50",
    "previous": null,
    "results": [
        {
            "id": "fa069c4b-4f6e-4349-88ac-8b6baf9d70c5",
            "name": "Device1",
            ...
        },
        {
            "id": "a37df58c-8bf3-4b97-bad5-301ef3880bea",
            "name": "Device2",
            ...
        },
        ...
    ]
}
```

The default page is determined by the [`PAGINATE_COUNT`](../../administration/configuration/optional-settings.md#paginate_count) configuration parameter, which defaults to 50. However, this can be overridden per request by specifying the desired `offset` and `limit` query parameters. For example, if you wish to retrieve a hundred devices at a time, you would make a request for:

```no-highlight
http://nautobot/api/dcim/devices/?limit=100
```

The response will return devices 1 through 100. The URL provided in the `next` attribute of the response will return devices 101 through 200:

```json
{
    "count": 2861,
    "next": "http://nautobot/api/dcim/devices/?limit=100&offset=100",
    "previous": null,
    "results": [...]
}
```

The maximum number of objects that can be returned is limited by the [`MAX_PAGE_SIZE`](../../administration/configuration/optional-settings.md#max_page_size) configuration parameter, which is 1000 by default. Setting this to `0` or `None` will remove the maximum limit. An API consumer can then pass `?limit=0` to retrieve _all_ matching objects with a single request.

!!! warning
    Disabling the page size limit introduces a potential for very resource-intensive requests, since one API request can effectively retrieve an entire table from the database.

## Sorting

By default, objects are sorted by their model-defined ordering property. However, this can be overridden by specifying the `?sort` query parameter. For example, to retrieve devices sorted by their rack position:

```no-highlight
http://nautobot/api/dcim/devices/?sort=position
```

To sort in descending order, prefix the field name with a minus sign (`-`):

```no-highlight
http://nautobot/api/dcim/devices/?sort=-position
```

Currently only direct model attributes are validated to be sorted as expected.

## Interacting with Objects

### Retrieving Multiple Objects

To query Nautobot for a list of objects, make a `GET` request to the model's _list_ endpoint. Objects are listed under the response object's `results` parameter. Specifying the `Accept` header with the Nautobot API version is not required, but is strongly recommended.

```no-highlight
curl -s -X GET \
-H "Accept: application/json; version=2.0" \
http://nautobot/api/ipam/ip-addresses/ | jq '.'
```

```json
{
  "count": 42031,
  "next": "http://nautobot/api/ipam/ip-addresses/?limit=50&offset=50",
  "previous": null,
  "results": [
    {
      "id": "bd307eca-de34-4bda-9195-d69ca52206d6",
      "address": "192.0.2.1/24",
      ...
    },
    {
      "id": "6c52e918-4f0c-4c50-ae49-6bef22c97fd5",
      "address": "192.0.2.2/24",
      ...
    },
    {
      "id": "b8cde1ee-1b86-4ea4-a884-041c472d8999",
      "address": "192.0.2.3/24",
      ...
    },
    ...
  ]
}
```

### Retrieving a Single Object

To query Nautobot for a single object, make a `GET` request to the model's _detail_ endpoint specifying its UUID.

!!! note
    Note that the trailing slash is required. Omitting this will return a 302 redirect.

```no-highlight
curl -s -X GET \
-H "Accept: application/json; version=2.0" \
http://nautobot/api/ipam/ip-addresses/bd307eca-de34-4bda-9195-d69ca52206d6/ | jq '.'
```

```json
{
  "id": "bd307eca-de34-4bda-9195-d69ca52206d6",
  "address": "192.0.2.1/24",
  ...
}
```

### Depth Query Parameter

+++ 2.0.0

A `?depth` query parameter is introduced in Nautobot 2.0 to replace the `?brief` parameter. It enables [nested serialization](https://www.django-rest-framework.org/api-guide/serializers/#specifying-nested-serialization) functionality and offers a more dynamic and comprehensive browsable API. It is available for both retrieving a single object and a list of objects.
This parameter is an positive integer value that can range from 0 to 10. In most use cases, you will only need a maximum `depth` of 2 to get all the information you need.

!!! note
    The `?brief` query parameter is removed for Nautobot v2.x. Use `?depth=0` instead.

!!! important
    The `?depth` query parameter should only be used for `GET` operations in the API. It should not be used in `POST`, `PATCH` and `DELETE` requests. For these requests, only `?depth=0` should be used.

#### Default/?depth=0

`?depth` parameter defaults to 0 and offers a very lightweight view of the API where all object-related fields are represented by a simple object, containing only the `id`, `object_type` and `url` attributes.

```no-highlight
curl -s -X GET \
-H "Accept: application/json; version=2.0" \
http://nautobot/api/dcim/locations/0e19e475-89c9-4cf4-8b5f-a0589f0950cd/ | jq '.'
```

```json
{
    "id": "0e19e475-89c9-4cf4-8b5f-a0589f0950cd",
    "display": "Campus-01",
    "url": "http://nautobot/api/dcim/locations/0e19e475-89c9-4cf4-8b5f-a0589f0950cd/",
    "tree_depth": 0,
    "time_zone": "Asia/Baghdad",
    "circuit_count": 7,
    "device_count": 0,
    "prefix_count": 0,
    "rack_count": 0,
    "virtual_machine_count": 0,
    "vlan_count": 0,
    "created": "2023-04-12T19:29:06.884754Z",
    "last_updated": "2023-04-12T19:29:06.906503Z",
    "name": "Campus-01",
    "description": "Local take each compare court exactly.",
    "facility": "328",
    "asn": null,
    "physical_address": "",
    "shipping_address": "",
    "latitude": null,
    "longitude": "104.200000",
    "contact_name": "Frances Hernandez",
    "contact_phone": "",
    "contact_email": "",
    "comments": "Sort share road candidate.",
    "status": {
        "id": "28eb334b-4171-4da4-a03a-fa6d0c6a9442",
        "object_type": "extras.status",
        "url": "http://nautobot/api/extras/statuses/28eb334b-4171-4da4-a03a-fa6d0c6a9442/",

    },
    "parent": null,
    "location_type": {
        "id": "e3d4a9af-c6c1-4582-b483-a13301eb6e28",
        "object_type": "dcim.locationtype",
        "url": "http://nautobot/api/dcim/location-types/e3d4a9af-c6c1-4582-b483-a13301eb6e28/",
    },
    "tenant": {
        "id": "5b1feadb-fab0-4f81-a53f-5192d83b0216",
        "object_type": "tenancy.tenant",
        "url": "http://nautobot/api/tenancy/tenants/5b1feadb-fab0-4f81-a53f-5192d83b0216/",
    },
    "tags": [
        {
            "id": "a50d4568-27ae-4743-87ac-ffdc22b7f5d2",
            "object_type": "extras.tag",
            "url": "http://nautobot/api/extras/tags/a50d4568-27ae-4743-87ac-ffdc22b7f5d2/",
        }
    ],
    "notes_url": "http://nautobot/api/dcim/locations/0e19e475-89c9-4cf4-8b5f-a0589f0950cd/notes/",
    "custom_fields": {
        "example_plugin_auto_custom_field": null
    }
}
```

#### ?depth=1

When `?depth=1` is added to the query parameters, all object-related fields, instead of being represented as light-weight objects as they are when `?depth=0`, will be represented as fully-detailed nested objects, similar (**but not necessarily identical!**) to the objects that would be retrieved when querying the API directly for those related objects.

!!! important
    Nested objects retrieved with a greater-than-zero `depth` parameter do not necessarily include all fields that would be included on the fully detailed object that can be retrieved by querying their `url` directly. In particular:

    - Nested objects *will not include* a field for `tags` or any other many-to-many relations on the object (such as a `Status` object's `content_types` relation).
    - Nested objects *will not include* the `relationships` or `computed_fields` keys, even if those are [opted-in](#retrieving-object-relationships-and-relationship-associations) on the request.
    - Nested objects *may omit* any derived (non-database) attributes, such as related object counts, tree-depth information, etc.

For example, retrieving a `Location` with `?depth=1` would provide nested objects for the `status`, `parent`, `location_type`, `tenant`, and `tags` fields:

```no-highlight
curl -s -X GET \
-H "Accept: application/json; version=2.0" \
http://nautobot/api/dcim/locations/ce69530e-6a4a-4d3c-9f95-fc326ec39abf/?depth=1 | jq '.'
```

```json
{
    ...
    "status": {
        "id": "91a53d61-4180-4820-835d-533b34dbb5b4",
        "display": "Active",
        "url": "http://nautobot/api/extras/statuses/91a53d61-4180-4820-835d-533b34dbb5b4/",
        "custom_fields": {},
        "notes_url": "http://nautobot/api/extras/statuses/91a53d61-4180-4820-835d-533b34dbb5b4/notes/",
        "created": "2023-04-12T00:00:00Z",
        "last_updated": "2023-04-12T19:25:51.413824Z",
        "name": "Active",
        "color": "4caf50",
        "description": "Unit is active"
    },
    "parent": {
        "id": "0e19e475-89c9-4cf4-8b5f-a0589f0950cd",
        "display": "Campus-01",
        "url": "http://nautobot/api/dcim/locations/0e19e475-89c9-4cf4-8b5f-a0589f0950cd/",
        "custom_fields": {
            "example_plugin_auto_custom_field": null
        },
        "notes_url": "http://nautobot/api/dcim/locations/0e19e475-89c9-4cf4-8b5f-a0589f0950cd/notes/",
        "tree_depth": null,
        "time_zone": "Asia/Baghdad",
        "created": "2023-04-12T19:29:06.884754Z",
        "last_updated": "2023-04-12T19:29:06.906503Z",
        "name": "Campus-01",
        "description": "Local take each compare court exactly.",
        "facility": "328",
        "asn": null,
        "physical_address": "",
        "shipping_address": "",
        "latitude": null,
        "longitude": "104.200000",
        "contact_name": "Frances Hernandez",
        "contact_phone": "",
        "contact_email": "",
        "comments": "Sort share road candidate.",
        "status": "http://nautobot/api/extras/statuses/28eb334b-4171-4da4-a03a-fa6d0c6a9442/",
        "parent": null,
        "location_type": "http://nautobot/api/extras/location-types/e3d4a9af-c6c1-4582-b483-a13301eb6e28/",
        "tenant": "http://nautobot/api/tenancy/tenants/5b1feadb-fab0-4f81-a53f-5192d83b0216/",
    },
    "location_type": {
        "id": "4edcc111-e3f7-4309-ab0e-eb34c001874e",
        "display": "Campus → Building",
        "url": "http://nautobot/api/dcim/location-types/4edcc111-e3f7-4309-ab0e-eb34c001874e/",
        "custom_fields": {},
        "notes_url": "http://nautobot/api/dcim/location-types/4edcc111-e3f7-4309-ab0e-eb34c001874e/notes/",
        "tree_depth": null,
        "created": "2023-04-12T19:29:06.707759Z",
        "last_updated": "2023-04-12T19:29:06.716482Z",
        "name": "Building",
        "description": "Protect growth bill all hair along.",
        "nestable": false,
        "parent": "http://nautobot/api/dcim/location-types/e3d4a9af-c6c1-4582-b483-a13301eb6e28/"
    },
    "tenant": {
        "id": "d043b6bc-6892-45f9-b460-4b006eb68016",
        "display": "Page Inc",
        "url": "http://nautobot/api/tenancy/tenants/d043b6bc-6892-45f9-b460-4b006eb68016/",
        "custom_fields": {},
        "notes_url": "http://nautobot/api/tenancy/tenants/d043b6bc-6892-45f9-b460-4b006eb68016/notes/",
        "created": "2023-04-12T19:29:06.257345Z",
        "last_updated": "2023-04-12T19:29:06.262563Z",
        "name": "Page Inc",
        "description": "Citizen father policy door science light. Glass improve place understand against ground.\nLarge firm per sing. Item they side walk test open tend.",
        "comments": "",
        "tenant_group": null,
    },
    "tags": [
        {
            "id": "a50d4568-27ae-4743-87ac-ffdc22b7f5d2",
            "display": "Light blue",
            "url": "http://nautobot/api/extras/tags/a50d4568-27ae-4743-87ac-ffdc22b7f5d2/",
            "custom_fields": {},
            "notes_url": "http://nautobot/api/extras/tags/a50d4568-27ae-4743-87ac-ffdc22b7f5d2/notes/",
            "name": "Light blue",
            "created": "2023-04-12T19:29:05.753433Z",
            "last_updated": "2023-04-12T19:29:05.770752Z",
            "color": "03a9f4",
            "description": "Want task generation. Commercial candidate performance financial guess modern.\nEarly toward adult black. Join black land sit. It smile standard possible reach."
        }
    ]
}
```

!!! note
    As previously explained, note that the `status` nested object included in this response does not include the `content_types` many-to-many relation that exists on all Status objects. If this information is needed, you would need to directly query the URL of the status object itself (above, `http://nautobot/api/extras/statuses/91a53d61-4180-4820-835d-533b34dbb5b4/`) to get a fully detailed response. Similarly, the `parent` and `tenant` nested objects do not include their `tags` relations, the `parent` object does not include its derived `tree_depth` and related object counters, and the `tags` nested object list does not include the `content_types` for each `Tag`.

#### ?depth=2 and beyond

A higher `depth` parameter in the query presents you with more insight to the object and can be useful in situations that demand information of an indirectly related field of the object.

!!! important
    Using higher `depth` values may substantially increase the amount of time it takes for the REST API to respond to your query when there are a large number of related objects. In some cases it may be more efficient to initially query with a lower `depth` and then follow the `url` values that the REST API response provides for specific related objects to query those objects directly as a more narrowly focused query approach.

For example, if you need information on the `parent` of a `location` instance's `parent`.

```no-highlight
curl -s -X GET \
-H "Accept: application/json; version=2.0" \
http://nautobot/api/dcim/locations/3b71a669-faa4-4f8d-a72a-8c94d121b793/?depth=2 | jq '.'
```

```json
{
    ...
    "parent": {
        ...
        "status": {
            "id": "39ea1ea4-3028-4a81-81e0-24a5743d3657",
            "url": "http://nautobot/api/extras/statuses/39ea1ea4-3028-4a81-81e0-24a5743d3657/",
            "display": "Retired",
            "object_type": "extras.status",
            "notes_url": "http://nautobot/api/extras/statuses/39ea1ea4-3028-4a81-81e0-24a5743d3657/notes/",
            "created": "2023-04-12T00:00:00Z",
            "last_updated": "2023-04-12T19:26:16.982697Z",
            "name": "Retired",
            "color": "f44336",
            "description": "Location has been retired",
            "custom_fields": {}
        },
        "parent": {
            "id": "0e19e475-89c9-4cf4-8b5f-a0589f0950cd",
            "url": "http://nautobot/api/dcim/locations/0e19e475-89c9-4cf4-8b5f-a0589f0950cd/",
            "display": "Campus-01",
            "object_type": "dcim.location",
            "time_zone": "Asia/Baghdad",
            "created": "2023-04-12T19:29:06.884754Z",
            "last_updated": "2023-04-12T19:29:06.906503Z",
            "name": "Campus-01",
            "description": "Local take each compare court exactly.",
            "facility": "328",
            "asn": null,
            "physical_address": "",
            "shipping_address": "",
            "latitude": null,
            "longitude": "104.200000",
            "contact_name": "Frances Hernandez",
            "contact_phone": "",
            "contact_email": "",
            "comments": "Sort share road candidate.",
            "status": "http://nautobot/api/extras/statuses/28eb334b-4171-4da4-a03a-fa6d0c6a9442/",
            "parent": null,
            "location_type": "http://nautobot/api/dcim/location-types/e3d4a9af-c6c1-4582-b483-a13301eb6e28/",
            "tenant": "http://nautobot/api/tenancy/tenants/5b1feadb-fab0-4f81-a53f-5192d83b0216/",
            "notes_url": "http://nautobot/api/dcim/locations/0e19e475-89c9-4cf4-8b5f-a0589f0950cd/notes/",
            "custom_fields": {
                "example_plugin_auto_custom_field": null
            }
        },
        "location_type": {
            "id": "4edcc111-e3f7-4309-ab0e-eb34c001874e",
            "display": "Campus → Building",
            "url": "http://nautobot/api/dcim/location-types/4edcc111-e3f7-4309-ab0e-eb34c001874e/",
            "created": "2023-04-12T19:29:06.707759Z",
            "last_updated": "2023-04-12T19:29:06.716482Z",
            "name": "Building",
            "description": "Protect growth bill all hair along.",
            "nestable": false,
            "parent": "http://nautobot/api/dcim/location-types/e3d4a9af-c6c1-4582-b483-a13301eb6e28/",
            "notes_url": "http://nautobot/api/dcim/location-types/4edcc111-e3f7-4309-ab0e-eb34c001874e/notes/",
            "custom_fields": {}
        },
        "tenant": null,
    },
    "location_type": {
        ...
        "parent": {
            "id": "4edcc111-e3f7-4309-ab0e-eb34c001874e",
            "display": "Campus → Building",
            "url": "http://nautobot/api/dcim/location-types/4edcc111-e3f7-4309-ab0e-eb34c001874e/",
            "created": "2023-04-12T19:29:06.707759Z",
            "last_updated": "2023-04-12T19:29:06.716482Z",
            "name": "Building",
            "description": "Protect growth bill all hair along.",
            "nestable": false,
            "parent": "http://nautobot/api/dcim/location-types/e3d4a9af-c6c1-4582-b483-a13301eb6e28/",
            "notes_url": "http://nautobot/api/dcim/location-types/4edcc111-e3f7-4309-ab0e-eb34c001874e/notes/",
            "custom_fields": {}
        }
    },
    ...
}
```

### Retrieving Object Relationships and Relationship Associations

+++ 1.4.0

Objects that are associated with another object by a custom [Relationship](../relationship.md) are also retrievable and modifiable via the REST API. Due to the additional processing overhead involved in retrieving and representing these relationships, they are _not_ included in default REST API `GET` responses. To include relationships data, pass `include=relationships` as a query parameter; in this case an additional key, `"relationships"`, will be included in the API response, as seen below:

```no-highlight
GET /api/dcim/locations/f472bb77-7f56-4e79-ac25-2dc73eb63924/?include=relationships
```

```json
{
    "id": "f472bb77-7f56-4e79-ac25-2dc73eb63924",
    "display": "alpha",
    "url": "http://nautobot/api/dcim/locations/f472bb77-7f56-4e79-ac25-2dc73eb63924/",
...
    "relationships": {
        "site-to-vrf": {
            "id": "e74cb7f7-15b0-499d-9401-a0f01cb96a9a",
            "url": "/api/extras/relationships/e74cb7f7-15b0-499d-9401-a0f01cb96a9a/",
            "name": "Single Site to Single VRF",
            "type": "one-to-one",
            "destination": {
                "label": "VRF",
                "object_type": "ipam.vrf",
                "objects": [
                    {
                        "id": "36641ba0-50d6-43be-b9b5-86aa992402e0",
                        "url": "http://nautobot/api/ipam/vrfs/36641ba0-50d6-43be-b9b5-86aa992402e0/",
                        "name": "red",
                        "rd": null,
                        "display": "red"
                    }
                ]
            }
        },
        "vrfs-to-locations": {
            "id": "e39c53e4-78cf-4572-b116-1d8830b81b2e",
            "url": "/api/extras/relationships/e39c53e4-78cf-4572-b116-1d8830b81b2e/",
            "name": "VRFs to Locations",
            "type": "many-to-many",
            "source": {
                "label": "VRFs",
                "object_type": "ipam.vrf",
                "objects": []
            }
        },
    }
}
```

* Under the `"relationships"` key, there will be one key per Relationship that applies to this model, corresponding to the `key` of that Relationship.
    * Under each key, there will be information about the Relationship itself, plus any of `"source"`, `"destination"`, or `"peer"` keys (depending on the type and directionality of the Relationship).
        * Under the `"source"`, `"destination"`, or `"peer"` keys, there are the following keys:
            * `"label"` - a human-readable description of the related objects
            * `"object_type"` - the content-type of the related objects
            * `"objects"` - a list of all related objects, each represented in nested-serializer form as described under [Related Objects](#related-objects) above.

In the example above we can see that a single VRF, `green`, is a destination for the `site-to-vrf` Relationship from this Site, while there are currently no VRFs associated as sources for the `vrfs-to-locations` Relationship to this Site.

### Including Config Contexts

When retrieving Devices and Virtual Machines via the REST API, it is possible to also retrive the rendered [configuration context data](../../core-data-model/extras/configcontext.md) for each such object if desired. Because rendering this data can be time consuming, it is _not_ included in the REST API responses by default. If you wish to include config context data in the response, you must opt in by specifying the query parameter `include=config_context` as a part of your request.

+/- 2.0.0
    In Nautobot 1.x, the rendered configuration context was included by default in the REST API response unless specifically excluded with the query parameter `exclude=config_context`. This behavior has been reversed in Nautobot 2.0 and the `exclude` query parameter is no longer supported.

### Creating a New Object

To create a new object, make a `POST` request to the model's _list_ endpoint with JSON data pertaining to the object being created. Note that a REST API token is required for all write operations; see the [authentication documentation](authentication.md) for more information. Also be sure to set the `Content-Type` HTTP header to `application/json`. As always, it's a good practice to also set the `Accept` HTTP header to include the requested REST API version.

```no-highlight
curl -s -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.0" \
http://nautobot/api/ipam/prefixes/ \
--data '{"prefix": "192.0.2.0/24", "status": "fc32b83f-2448-4602-9d43-fecc6735e4e5", "location": "8df9e629-4338-438b-8ea9-06114f7be08e", "namespace": "1fa6a1a9-84a3-4cf3-a9ad-7e4e7baa134a"}' | jq '.'
```

```json
{
  "id": "48df6965-0fcb-4155-b5f8-00fe8b9b01af",
  "url": "http://nautobot/api/ipam/prefixes/48df6965-0fcb-4155-b5f8-00fe8b9b01af/",
  "family": {
    "value": 4,
    "label": "IPv4"
  },
  "prefix": "192.0.2.0/24",
  "location": {
    "id": "8df9e629-4338-438b-8ea9-06114f7be08e",
    "object_type": "dcim.location",
    "url": "http://nautobot/api/dcim/locations/8df9e629-4338-438b-8ea9-06114f7be08e/",
  },
  "namespace": {
    "id": "1fa6a1a9-84a3-4cf3-a9ad-7e4e7baa134a",
    "object_type": "ipam.namespace",
    "url": "http://nautobot/api/ipam/namespaces/1fa6a1a9-84a3-4cf3-a9ad-7e4e7baa134a/",
  },
  "tenant": null,
  "vlan": null,
  "status": {
    "id": "fc32b83f-2448-4602-9d43-fecc6735e4e5",
    "object_type": "extras.status",
    "url": "http://nautobot/api/extras/statuses/fc32b83f-2448-4602-9d43-fecc6735e4e5/",
  },
  "role": null,
  "type": "network",
  "description": "",
  "tags": [],
  "custom_fields": {},
  "created": "2020-08-04T20:08:39.007125Z",
  "last_updated": "2020-08-04T20:08:39.007125Z"
}
```

Related fields can be specified using either the primary key, the URL of the related object, or a nested representation similar to what is returned in the `?depth=0` response. For example, the following request is equivalent to the one above:

```no-highlight
curl -s -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.0" \
http://nautobot/api/ipam/prefixes/ \
--data '{"prefix": "192.0.2.0/24", "status": {"id": "fc32b83f-2448-4602-9d43-fecc6735e4e5", "object_type": "extras.status"}, "location": {"id": "8df9e629-4338-438b-8ea9-06114f7be08e", "object_type": "dcim.location"}, "namespace": { "id": "1fa6a1a9-84a3-4cf3-a9ad-7e4e7baa134a", "object_type": "ipam.namespace"} }' | jq '.'
```

### Creating Multiple Objects

To create multiple instances of a model using a single request, make a `POST` request to the model's _list_ endpoint with a list of JSON objects representing each instance to be created. If successful, the response will contain a list of the newly created instances. The example below illustrates the creation of three new locations.

```no-highlight
curl -X POST -H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.0; indent=4" \
http://nautobot/api/dcim/locations/ \
--data '[
{"name": "Location 1", "parent": {"name": "United States"}, "location_type": {"name": "City"}},
{"name": "Location 2", "parent": {"name": "United States"}, "location_type": {"name": "City"}},
{"name": "Location 3", "parent": {"name": "United States"}, "location_type": {"name": "City"}},
]'
```

```json
[
    {
        "id": "0238a4e3-66f2-455a-831f-5f177215de0f",
        "url": "http://nautobot/api/dcim/locations/0238a4e3-66f2-455a-831f-5f177215de0f/",
        "name": "Location 1",
        ...
    },
    {
        "id": "33ac3a3b-0ee7-49b7-bf2a-244096051dc0",
        "url": "http://nautobot/api/dcim/locations/33ac3a3b-0ee7-49b7-bf2a-244096051dc0/",
        "name": "Location 2",
        ...
    },
    {
        "id": "10b3134d-960b-4794-ad18-0e73edd357c4",
        "url": "http://nautobot/api/dcim/locations/10b3134d-960b-4794-ad18-0e73edd357c4/",
        "name": "Location 3",
        ...
    }
]
```

### Updating an Object

To modify an object which has already been created, make a `PATCH` request to the model's _detail_ endpoint specifying its UUID. Include any data which you wish to update on the object. As with object creation, the `Authorization` and `Content-Type` headers must also be specified, and specifying the `Accept` header is also strongly recommended.

```no-highlight
curl -s -X PATCH \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.0" \
http://nautobot/api/ipam/prefixes/b484b0ac-12e3-484a-84c0-aa17955eaedc/ \
--data '{"status": "fc32b83f-2448-4602-9d43-fecc6735e4e5"}' | jq '.'
```

```json
{
  "id": "48df6965-0fcb-4155-b5f8-00fe8b9b01af",
  "url": "http://nautobot/api/ipam/prefixes/48df6965-0fcb-4155-b5f8-00fe8b9b01af/",
  "family": {
    "value": 4,
    "label": "IPv4"
  },
  "prefix": "192.0.2.0/24",
  "site": "http://nautobot/api/dcim/locations/8df9e629-4338-438b-8ea9-06114f7be08e/",
  "vrf": null,
  "tenant": null,
  "vlan": null,
  "status": "http://nautobot/api/extras/statuses/fc32b83f-2448-4602-9d43-fecc6735e4e5/",
  "role": null,
  "type": "network",
  "description": "",
  "tags": [],
  "custom_fields": {},
  "created": "2020-08-04T00:00:00Z",
  "last_updated": "2020-08-04T20:14:55.709430Z"
}
```

!!! note "PUT versus PATCH"
    The Nautobot REST API support the use of either `PUT` or `PATCH` to modify an existing object. The difference is that a `PUT` request requires the user to specify a _complete_ representation of the object being modified, whereas a `PATCH` request need include only the attributes that are being updated. For most purposes, using `PATCH` is recommended.

#### Updating Relationship Associations

+++ 1.4.0

It is possible to modify the objects associated via Relationship with an object as part of a REST API `PATCH` request by specifying the `"relationships"` key, any or all of the relevant Relationships, and the list of desired related objects for each such Relationship. Since nested serializers are used for the related objects, they can be identified by ID (primary key) or by one or more attributes in a dictionary. For example, either of the following requests would be valid:

```json
{
    "relationships": {
        "site_to_vrf": {
            "destination": {
                "objects": [
                    {"name": "blue"}
                ]
            }
        },
        "vrfs_to_locations": {
            "source": {
                "objects": [
                    {"name": "green"},
                    {"name": "red"},
                ]
            }
        }
    }
}
```

```json
{
    "relationships": {
        "site_to_vrf": {
            "destination": {
                "objects": ["3e3c58f9-4f63-44ba-acee-f0c42430eba7"]
            }
        }
    }
}
```

!!! Note
    Relationship keys can be omitted from the `"relationships"` dictionary, in which case the associations for that Relationship will be left unmodified. In the second example above, the existing association for the `"site_to_vrf"` Relationship would be replaced, but the `"vrfs_to_locations"` Relationship's associations would remain as-is.

### Updating Multiple Objects

Multiple objects can be updated simultaneously by issuing a `PUT` or `PATCH` request to a model's list endpoint with a list of dictionaries specifying the UUID of each object to be deleted and the attributes to be updated. For example, to update locations with UUIDs 18de055e-3ea9-4cc3-ba78-b7eef6f0d589 and 1a414273-3d68-4586-ba22-6ae0a5702b8f to a status of "Active", issue the following request:

```no-highlight
curl -s -X PATCH \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.0" \
http://nautobot/api/dcim/locations/ \
--data '[{"id": "18de055e-3ea9-4cc3-ba78-b7eef6f0d589", "status": {"name": "Active"}}, {"id": "1a414273-3d68-4586-ba22-6ae0a5702b8f", "status": {"name": "Active"}}]'
```

Note that there is no requirement for the attributes to be identical among objects. For instance, it's possible to update the status of one site along with the name of another in the same request.

!!! note
    The bulk update of objects is an all-or-none operation, meaning that if Nautobot fails to successfully update any of the specified objects (e.g. due a validation error), the entire operation will be aborted and none of the objects will be updated.

### Deleting an Object

To delete an object from Nautobot, make a `DELETE` request to the model's _detail_ endpoint specifying its UUID. The `Authorization` header must be included to specify an authorization token, however this type of request does not support passing any data in the body.

```no-highlight
curl -s -X DELETE \
-H "Authorization: Token $TOKEN" \
-H "Accept: application/json; version=2.0" \
http://nautobot/api/ipam/prefixes/48df6965-0fcb-4155-b5f8-00fe8b9b01af/
```

Note that `DELETE` requests do not return any data: If successful, the API will return a 204 (No Content) response.

!!! note
    You can run `curl` with the verbose (`-v`) flag to inspect the HTTP response codes.

### Deleting Multiple Objects

Nautobot supports the simultaneous deletion of multiple objects of the same type by issuing a `DELETE` request to the model's list endpoint with a list of dictionaries specifying the UUID of each object to be deleted. For example, to delete locations with UUIDs 18de055e-3ea9-4cc3-ba78-b7eef6f0d589, 1a414273-3d68-4586-ba22-6ae0a5702b8f, and c2516019-caf6-41f0-98a6-4276c1a73fa3, issue the following request:

```no-highlight
curl -s -X DELETE \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.0" \
http://nautobot/api/dcim/locations/ \
--data '[{"id": "18de055e-3ea9-4cc3-ba78-b7eef6f0d589"}, {"id": "1a414273-3d68-4586-ba22-6ae0a5702b8f"}, {"id": "c2516019-caf6-41f0-98a6-4276c1a73fa3"}]'
```

!!! note
    The bulk deletion of objects is an all-or-none operation, meaning that if Nautobot fails to delete any of the specified objects (e.g. due a dependency by a related object), the entire operation will be aborted and none of the objects will be deleted.
