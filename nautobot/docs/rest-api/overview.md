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
curl -s http://nautobot/api/ipam/ip-addresses/c557df87-9a63-4555-bfd1-21cea2f6aac3/ | jq '.'
```

```json
{
  "id": 2954,
  "url": "http://nautobot/api/ipam/ip-addresses/c557df87-9a63-4555-bfd1-21cea2f6aac3/",
  "family": {
    "value": 4,
    "label": "IPv4"
  },
  "address": "192.168.0.42/26",
  "vrf": null,
  "tenant": null,
  "status": {
    "value": "active",
    "label": "Active"
  },
  "role": null,
  "assigned_object_type": "dcim.interface",
  "assigned_object_id": "9fd066d2-135c-4005-b032-e0551cc61cec",
  "assigned_object": {
    "id": "9fd066d2-135c-4005-b032-e0551cc61cec",
    "url": "http://nautobot/api/dcim/interfaces/9fd066d2-135c-4005-b032-e0551cc61cec/",
    "device": {
      "id": "6a522ebb-5739-4c5c-922f-ab4a2dc12eb0",
      "url": "http://nautobot/api/dcim/devices/6a522ebb-5739-4c5c-922f-ab4a2dc12eb0/",
      "name": "router1",
      "display": "router1"
    },
    "name": "et-0/1/2",
    "cable": null,
    "connection_status": null
  },
  "nat_inside": null,
  "nat_outside": null,
  "dns_name": "",
  "description": "Example IP address",
  "tags": [],
  "custom_fields": {},
  "created": "2020-08-04",
  "last_updated": "2020-08-04T14:12:39.666885Z"
}
```

Each attribute of the IP address is expressed as an attribute of the JSON object. Fields may include their own nested objects, as in the case of the `assigned_object` field above. Every object includes a primary key named `id` which uniquely identifies it in the database.

## Interactive Documentation

Comprehensive, interactive documentation of all REST API endpoints is available on a running Nautobot instance at `/api/docs/`. This interface provides a convenient sandbox for researching and experimenting with specific endpoints and request types. The API itself can also be explored using a web browser by navigating to its root at `/api/`.

+++ 1.3.0
    You can view or explore a specific REST API [version](#versioning) by adding the API version as a query parameter, for example `/api/docs/?api_version=1.3` or `/api/?api_version=1.2`

## Endpoint Hierarchy

Nautobot's entire REST API is housed under the API root at `https://<hostname>/api/`. The URL structure is divided at the root level by application: circuits, DCIM, extras, IPAM, plugins, tenancy, users, and virtualization. Within each application exists a separate path for each model. For example, the provider and circuit objects are located under the "circuits" application:

* `/api/circuits/providers/`
* `/api/circuits/circuits/`

Likewise, the site, rack, and device objects are located under the "DCIM" application:

* `/api/dcim/sites/`
* `/api/dcim/racks/`
* `/api/dcim/devices/`

The full hierarchy of available endpoints can be viewed by navigating to the API root in a web browser.

Each model generally has two views associated with it: a list view and a detail view. The list view is used to retrieve a list of multiple objects and to create new objects. The detail view is used to retrieve, update, or delete an single existing object. All objects are referenced by their UUID primary key (`id`).

* `/api/dcim/devices/` - List existing devices or create a new device
* `/api/dcim/devices/6a522ebb-5739-4c5c-922f-ab4a2dc12eb0/` - Retrieve, update, or delete the device with ID 6a522ebb-5739-4c5c-922f-ab4a2dc12eb0

Lists of objects can be filtered using a set of query parameters. For example, to find all interfaces belonging to the device with ID 6a522ebb-5739-4c5c-922f-ab4a2dc12eb0:

```no-highlight
GET /api/dcim/interfaces/?device_id=6a522ebb-5739-4c5c-922f-ab4a2dc12eb0
```

See the [filtering documentation](filtering.md) for more details.

## Versioning

+++ 1.3.0

As of Nautobot 1.3, the REST API supports multiple versions. A REST API client may request a given API version by including a `major.minor` Nautobot version number in its request in one of two ways:

1. A client may include a `version` in its HTTP Accept header, for example `Accept: application/json; version=1.3`
2. A client may include an `api_version` as a URL query parameter, for example `/api/extras/jobs/?api_version=1.3`

Generally the former approach is recommended when writing automated API integrations, as it can be set as a general request header alongside the [authentication token](authentication.md) and re-used across a series of REST API interactions, while the latter approach may be more convenient when initially exploring the REST API via the interactive documentation as described above.

### Default Versions and Backward Compatibility

By default, a REST API request that does not specify an API version number will default to compatibility with a specified Nautobot version. This default REST API version can be expected to remain constant throughout the lifespan of a given Nautobot major release.

!!! note
    For Nautobot 1.x, the default API behavior is to be compatible with the REST API of Nautobot version 1.2, in other words, for all Nautobot 1.x versions (beginning with Nautobot 1.2.0), `Accept: application/json` is functionally equivalent to `Accept: application/json; version=1.2`.

!!! tip
    The default REST API version compatibility may change in a subsequent Nautobot major release, so as a best practice, it is recommended that a REST API client _should always_ request the exact Nautobot REST API version that it is compatible with, rather than relying on the default behavior to remain constant.

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
* Addition of new, _required_ fields in POST/PUT/PATCH requests
* Changed field types (for example, changing a single value to a list of values)
* Redesigned API (for example, listing and accessing Job instances by UUID primary-key instead of by class-path string)

Per Nautobot's [feature-deprecation policy](../development/index.md#deprecation-policy), the previous REST API version will continue to be supported for some time before eventually being removed.

!!! important
    When breaking changes are introduced in a minor release, for compatibility as described above, the default REST API behavior within the remainder of the current major release cycle will continue to be the previous (unchanged) API version. API clients must "opt in" to the new version of the API by explicitly requesting the new API version.

!!! tip
    This is another reason to always specify the exact `major.minor` Nautobot REST API version when developing a REST API client integration, as it guarantees that the client will be receiving the latest API feature set available in that release rather than possibly defaulting to an older REST API version that is still default but is now deprecated.

### Example of API Version Behavior

As an example, let us say that Nautobot 1.3 introduced a new, _non-backwards-compatible_ REST API for the `/api/extras/jobs/` endpoint, and also introduced a new, _backwards-compatible_ set of additional fields on the `/api/dcim/sites/` endpoint. Depending on what API version a REST client interacting with Nautobot 1.3 specified (or didn't specify), it would see the following responses from the server:

| API endpoint        | Requested API version | Response                                     |
| ------------------- | --------------------- | -------------------------------------------- |
| `/api/extras/jobs/` | (unspecified)         | Deprecated 1.2-compatible REST API           |
| `/api/extras/jobs/` | `1.2`                 | Deprecated 1.2-compatible REST API           |
| `/api/extras/jobs/` | `1.3`                 | New/updated 1.3-compatible REST API          |

!!! important
    Note again that if not specifying an API version, the client _would not_ receive the latest API version when breaking changes are present. Even though the server had Nautobot version 1.3, the default Jobs REST API behavior would be that of Nautobot 1.2. Only by actually requesting API version `1.3` was the client able to access the new Jobs REST API.

| API endpoint        | Requested API version | Response                                     |
| ------------------- | --------------------- | -------------------------------------------- |
| `/api/dcim/sites/`  | (unspecified)         | 1.3-updated, 1.2-compatible REST API         |
| `/api/dcim/sites/`  | `1.2`                 | 1.3-updated, 1.2-compatible REST API         |
| `/api/dcim/sites/`  | `1.3`                 | 1.3-updated, 1.2-compatible REST API         |

| API endpoint        | Requested API version | Response                                     |
| ------------------- | --------------------- | -------------------------------------------- |
| `/api/dcim/racks/`  | (unspecified)         | 1.2-compatible REST API (unchanged)          |
| `/api/dcim/racks/`  | `1.2`                 | 1.2-compatible REST API (unchanged)          |
| `/api/dcim/racks/`  | `1.3`                 | 1.3-compatible REST API (unchanged from 1.2) |

### APISelect with versioning capability

+++ 1.3.0

The constructor for Nautobot's `APISelect`/`APISelectMultiple` UI widgets now includes an optional `api_version` argument which if set overrides the default API version of the request.

## Serialization

The REST API employs two types of serializers to represent model data: base serializers and nested serializers. The base serializer is used to present the complete view of a model. This includes all database table fields which comprise the model, and may include additional metadata. A base serializer includes relationships to parent objects, but **does not** include child objects. For example, the `VLANSerializer` includes a nested representation its parent VLANGroup (if any), but does not include any assigned Prefixes.

```json
{
    "id": 1048,
    "site": {
        "id": "09c9e21c-e038-44fd-be9a-43aef97bff8f",
        "url": "http://nautobot/api/dcim/sites/09c9e21c-e038-44fd-be9a-43aef97bff8f/",
        "name": "Corporate HQ",
        "slug": "corporate-hq"
    },
    "group": {
        "id": "eccc0964-9fab-43bc-bb77-66b1be08f64b",
        "url": "http://nautobot/api/ipam/vlan-groups/eccc0964-9fab-43bc-bb77-66b1be08f64b/",
        "name": "Production",
        "slug": "production"
    },
    "vid": 101,
    "name": "Users-Floor1",
    "tenant": null,
    "status": {
        "value": "active",
        "label": "Active"
    },
    "role": {
        "id": "a1fd5e46-a85e-48c3-a2f4-3c2ec2bb2464",
        "url": "http://nautobot/api/ipam/roles/a1fd5e46-a85e-48c3-a2f4-3c2ec2bb2464/",
        "name": "User Access",
        "slug": "user-access"
    },
    "description": "",
    "display": "101 (Users-Floor1)",
    "custom_fields": {}
}
```

### Related Objects

Related objects (e.g. `ForeignKey` fields) are represented using nested serializers. A nested serializer provides a minimal representation of an object, including only its direct URL and enough information to display the object to a user. When performing write API actions (`POST`, `PUT`, and `PATCH`), related objects may be specified by either UUID (primary key), or by a set of attributes sufficiently unique to return the desired object.

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
        "site": {
            "name": "Equinix DC6"
        },
        "name": "R204"
    },
    ...
}
```

Note that if the provided parameters do not return exactly one object, a validation error is raised.

### Generic Relations

Some objects within Nautobot have attributes which can reference an object of multiple types, known as _generic relations_. For example, an IP address can be assigned to either a device interface _or_ a virtual machine interface. When making this assignment via the REST API, we must specify two attributes:

* `assigned_object_type` - The content type of the assigned object, defined as `<app>.<model>`
* `assigned_object_id` - The assigned object's UUID

Together, these values identify a unique object in Nautobot. The assigned object (if any) is represented by the `assigned_object` attribute on the IP address model.

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
http://nautobot/api/ipam/ip-addresses/ \
--data '{
    "address": "192.0.2.1/24",
    "assigned_object_type": "dcim.interface",
    "assigned_object_id": "e824bc29-623f-407e-8aa8-828f4c0b98ee"
}'
```

```json
{
    "id": "e2f29f8f-002a-4c4a-9d19-24cc7549e715",
    "url": "http://nautobot/api/ipam/ip-addresses/56296/",
    "assigned_object_type": "dcim.interface",
    "assigned_object_id": "e824bc29-623f-407e-8aa8-828f4c0b98ee",
    "assigned_object": {
        "id": "e824bc29-623f-407e-8aa8-828f4c0b98ee",
        "url": "http://nautobot/api/dcim/interfaces/e824bc29-623f-407e-8aa8-828f4c0b98ee/",
        "device": {
            "id": "76816a69-db2c-40e6-812d-115c61156e21",
            "url": "http://nautobot/api/dcim/devices/76816a69-db2c-40e6-812d-115c61156e21/",
            "name": "device105",
            "display": "device105"
        },
        "name": "ge-0/0/0",
        "cable": null,
        "connection_status": null
    },
    ...
}
```

If we wanted to assign this IP address to a virtual machine interface instead, we would have set `assigned_object_type` to `virtualization.vminterface` and updated the object ID appropriately.

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

The default page is determined by the [`PAGINATE_COUNT`](../configuration/optional-settings.md#paginate_count) configuration parameter, which defaults to 50. However, this can be overridden per request by specifying the desired `offset` and `limit` query parameters. For example, if you wish to retrieve a hundred devices at a time, you would make a request for:

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

The maximum number of objects that can be returned is limited by the [`MAX_PAGE_SIZE`](../configuration/optional-settings.md#max_page_size) configuration parameter, which is 1000 by default. Setting this to `0` or `None` will remove the maximum limit. An API consumer can then pass `?limit=0` to retrieve _all_ matching objects with a single request.

!!! warning
    Disabling the page size limit introduces a potential for very resource-intensive requests, since one API request can effectively retrieve an entire table from the database.

## Interacting with Objects

### Retrieving Multiple Objects

To query Nautobot for a list of objects, make a `GET` request to the model's _list_ endpoint. Objects are listed under the response object's `results` parameter. Specifying the `Accept` header with the Nautobot API version is not required, but is strongly recommended.

```no-highlight
curl -s -X GET \
-H "Accept: application/json; version=1.3" \
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
-H "Accept: application/json; version=1.3" \
http://nautobot/api/ipam/ip-addresses/bd307eca-de34-4bda-9195-d69ca52206d6/ | jq '.'
```

```json
{
  "id": "bd307eca-de34-4bda-9195-d69ca52206d6",
  "address": "192.0.2.1/24",
  ...
}
```

### Brief Format

The `GET` API endpoints support an optional "brief" format, which returns only a minimal representation of each object in the response. This is useful when you need only a list of available objects without any related data, such as when populating a drop-down list in a form. As an example, the default (complete) format of an IP address looks like this:

```no-highlight
GET /api/ipam/prefixes/7d2d24ac-4737-4fc1-a850-b30366618f3d/
```

```json
{
    "id": "7d2d24ac-4737-4fc1-a850-b30366618f3d",
    "url": "http://nautobot/api/ipam/prefixes/7d2d24ac-4737-4fc1-a850-b30366618f3d/",
    "family": {
        "value": 4,
        "label": "IPv4"
    },
    "prefix": "192.0.2.0/24",
    "site": {
        "id": "b9edf2ee-cad9-48be-9921-006294bff730",
        "url": "http://nautobot/api/dcim/sites/b9edf2ee-cad9-48be-9921-006294bff730/",
        "name": "Site 23A",
        "slug": "site-23a"
    },
    "vrf": null,
    "tenant": null,
    "vlan": null,
    "status": {
        "value": "container",
        "label": "Container"
    },
    "role": {
        "id": "ae1470bc-a858-4ce7-b9ce-dd1cd46333fe",
        "url": "http://nautobot/api/ipam/roles/ae1470bc-a858-4ce7-b9ce-dd1cd46333fe/",
        "name": "Staging",
        "slug": "staging"
    },
    "is_pool": false,
    "description": "Example prefix",
    "tags": [],
    "custom_fields": {},
    "created": "2018-12-10",
    "last_updated": "2019-03-01T20:02:46.173540Z"
}
```

The brief format is much more terse:

```no-highlight
GET /api/ipam/prefixes/7d2d24ac-4737-4fc1-a850-b30366618f3d/?brief=1
```

```json
{
    "id": "7d2d24ac-4737-4fc1-a850-b30366618f3d",
    "url": "http://nautobot/api/ipam/prefixes/7d2d24ac-4737-4fc1-a850-b30366618f3d/",
    "family": 4,
    "prefix": "10.40.3.0/24"
}
```

The brief format is supported for both lists and individual objects.

### Retrieving Object Relationships and Relationship Associations

+++ 1.4.0

Objects that are associated with another object by a custom [Relationship](../models/extras/relationship.md) are also retrievable and modifiable via the REST API. Due to the additional processing overhead involved in retrieving and representing these relationships, they are _not_ included in default REST API `GET` responses. To include relationships data, pass `include=relationships` as a query parameter; in this case an additional key, `"relationships"`, will be included in the API response, as seen below:

```no-highlight
GET /api/dcim/sites/f472bb77-7f56-4e79-ac25-2dc73eb63924/?include=relationships
```

```json
{
    "id": "f472bb77-7f56-4e79-ac25-2dc73eb63924",
    "display": "alpha",
    "url": "http://nautobot/api/dcim/sites/f472bb77-7f56-4e79-ac25-2dc73eb63924/",
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
        "vrfs-to-sites": {
            "id": "e39c53e4-78cf-4572-b116-1d8830b81b2e",
            "url": "/api/extras/relationships/e39c53e4-78cf-4572-b116-1d8830b81b2e/",
            "name": "VRFs to Sites",
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

* Under the `"relationships"` key, there will be one key per Relationship that applies to this model, corresponding to the `slug` of that Relationship.
    * Under each slug key, there will be information about the Relationship itself, plus any of `"source"`, `"destination"`, or `"peer"` keys (depending on the type and directionality of the Relationship).
        * Under the `"source"`, `"destination"`, or `"peer"` keys, there are the following keys:
            * `"label"` - a human-readable description of the related objects
            * `"object_type"` - the content-type of the related objects
            * `"objects"` - a list of all related objects, each represented in nested-serializer form as described under [Related Objects](#related-objects) above.

In the example above we can see that a single VRF, `green`, is a destination for the `site-to-vrf` Relationship from this Site, while there are currently no VRFs associated as sources for the `vrfs-to-sites` Relationship to this Site.

### Excluding Config Contexts

When retrieving devices and virtual machines via the REST API, each will include its rendered [configuration context data](../models/extras/configcontext.md) by default. Users with large amounts of context data will likely observe suboptimal performance when returning multiple objects, particularly with very high page sizes. To combat this, context data may be excluded from the response data by attaching the query parameter `?exclude=config_context` to the request. This parameter works for both list and detail views.

### Creating a New Object

To create a new object, make a `POST` request to the model's _list_ endpoint with JSON data pertaining to the object being created. Note that a REST API token is required for all write operations; see the [authentication documentation](authentication.md) for more information. Also be sure to set the `Content-Type` HTTP header to `application/json`. As always, it's a good practice to also set the `Accept` HTTP header to include the requested REST API version.

```no-highlight
curl -s -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3" \
http://nautobot/api/ipam/prefixes/ \
--data '{"prefix": "192.0.2.0/24", "site": 8df9e629-4338-438b-8ea9-06114f7be08e}' | jq '.'
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
  "site": {
    "id": "8df9e629-4338-438b-8ea9-06114f7be08e",
    "url": "http://nautobot/api/dcim/sites/8df9e629-4338-438b-8ea9-06114f7be08e/",
    "name": "US-East 4",
    "slug": "us-east-4"
  },
  "vrf": null,
  "tenant": null,
  "vlan": null,
  "status": {
    "value": "active",
    "label": "Active"
  },
  "role": null,
  "is_pool": false,
  "description": "",
  "tags": [],
  "custom_fields": {},
  "created": "2020-08-04",
  "last_updated": "2020-08-04T20:08:39.007125Z"
}
```

### Creating Multiple Objects

To create multiple instances of a model using a single request, make a `POST` request to the model's _list_ endpoint with a list of JSON objects representing each instance to be created. If successful, the response will contain a list of the newly created instances. The example below illustrates the creation of three new sites.

```no-highlight
curl -X POST -H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
http://nautobot/api/dcim/sites/ \
--data '[
{"name": "Site 1", "slug": "site-1", "region": {"name": "United States"}},
{"name": "Site 2", "slug": "site-2", "region": {"name": "United States"}},
{"name": "Site 3", "slug": "site-3", "region": {"name": "United States"}}
]'
```

```json
[
    {
        "id": "0238a4e3-66f2-455a-831f-5f177215de0f",
        "url": "http://nautobot/api/dcim/sites/0238a4e3-66f2-455a-831f-5f177215de0f/",
        "name": "Site 1",
        ...
    },
    {
        "id": "33ac3a3b-0ee7-49b7-bf2a-244096051dc0",
        "url": "http://nautobot/api/dcim/sites/33ac3a3b-0ee7-49b7-bf2a-244096051dc0/",
        "name": "Site 2",
        ...
    },
    {
        "id": "10b3134d-960b-4794-ad18-0e73edd357c4",
        "url": "http://nautobot/api/dcim/sites/10b3134d-960b-4794-ad18-0e73edd357c4/",
        "name": "Site 3",
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
-H "Accept: application/json; version=1.3" \
http://nautobot/api/ipam/prefixes/b484b0ac-12e3-484a-84c0-aa17955eaedc/ \
--data '{"status": "reserved"}' | jq '.'
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
  "site": {
    "id": "8df9e629-4338-438b-8ea9-06114f7be08e",
    "url": "http://nautobot/api/dcim/sites/8df9e629-4338-438b-8ea9-06114f7be08e/",
    "name": "US-East 4",
    "slug": "us-east-4"
  },
  "vrf": null,
  "tenant": null,
  "vlan": null,
  "status": {
    "value": "reserved",
    "label": "Reserved"
  },
  "role": null,
  "is_pool": false,
  "description": "",
  "tags": [],
  "custom_fields": {},
  "created": "2020-08-04",
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
        "site-to-vrf": {
            "destination": {
                "objects": [
                    {"name": "blue"}
                ]
            }
        },
        "vrfs-to-sites": {
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
        "site-to-vrf": {
            "destination": {
                "objects": ["3e3c58f9-4f63-44ba-acee-f0c42430eba7"]
            }
        }
    }
}
```

!!! Note
    Relationship slugs can be omitted from the `"relationships"` dictionary, in which case the associations for that Relationship will be left unmodified. In the second example above, the existing association for the `"site-to-vrf"` Relationship would be replaced, but the `"vrfs-to-sites"` Relationship's associations would remain as-is.

### Updating Multiple Objects

Multiple objects can be updated simultaneously by issuing a `PUT` or `PATCH` request to a model's list endpoint with a list of dictionaries specifying the UUID of each object to be deleted and the attributes to be updated. For example, to update sites with UUIDs 18de055e-3ea9-4cc3-ba78-b7eef6f0d589 and 1a414273-3d68-4586-ba22-6ae0a5702b8f to a status of "active", issue the following request:

```no-highlight
curl -s -X PATCH \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3" \
http://nautobot/api/dcim/sites/ \
--data '[{"id": "18de055e-3ea9-4cc3-ba78-b7eef6f0d589", "status": "active"}, {"id": "1a414273-3d68-4586-ba22-6ae0a5702b8f", "status": "active"}]'
```

Note that there is no requirement for the attributes to be identical among objects. For instance, it's possible to update the status of one site along with the name of another in the same request.

!!! note
    The bulk update of objects is an all-or-none operation, meaning that if Nautobot fails to successfully update any of the specified objects (e.g. due a validation error), the entire operation will be aborted and none of the objects will be updated.

### Deleting an Object

To delete an object from Nautobot, make a `DELETE` request to the model's _detail_ endpoint specifying its UUID. The `Authorization` header must be included to specify an authorization token, however this type of request does not support passing any data in the body.

```no-highlight
curl -s -X DELETE \
-H "Authorization: Token $TOKEN" \
-H "Accept: application/json; version=1.3" \
http://nautobot/api/ipam/prefixes/48df6965-0fcb-4155-b5f8-00fe8b9b01af/
```

Note that `DELETE` requests do not return any data: If successful, the API will return a 204 (No Content) response.

!!! note
    You can run `curl` with the verbose (`-v`) flag to inspect the HTTP response codes.

### Deleting Multiple Objects

Nautobot supports the simultaneous deletion of multiple objects of the same type by issuing a `DELETE` request to the model's list endpoint with a list of dictionaries specifying the UUID of each object to be deleted. For example, to delete sites with UUIDs 18de055e-3ea9-4cc3-ba78-b7eef6f0d589, 1a414273-3d68-4586-ba22-6ae0a5702b8f, and c2516019-caf6-41f0-98a6-4276c1a73fa3, issue the following request:

```no-highlight
curl -s -X DELETE \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3" \
http://nautobot/api/dcim/sites/ \
--data '[{"id": "18de055e-3ea9-4cc3-ba78-b7eef6f0d589"}, {"id": "1a414273-3d68-4586-ba22-6ae0a5702b8f"}, {"id": "c2516019-caf6-41f0-98a6-4276c1a73fa3"}]'
```

!!! note
    The bulk deletion of objects is an all-or-none operation, meaning that if Nautobot fails to delete any of the specified objects (e.g. due a dependency by a related object), the entire operation will be aborted and none of the objects will be deleted.
