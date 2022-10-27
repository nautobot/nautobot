# GraphQL

Nautobot supports a Read-Only GraphQL interface that can be used to query most information present in the database. The GraphQL interface is available at the endpoint `graphql/` for a human to explore and GraphQL can be queried as an API via the endpoint `api/graphql/`. Currently the support for GraphQL is limited to `query`, other operation type like `mutations` and `subscriptions` are not supported. Additionally, GraphQL variables are supported.

The GraphQL implementation is leveraging the `graphene-django` library and supports the [standard GraphQL language](https://graphql.org/learn/queries/).

## How to use the GraphQL interface

The GraphQL interface can be used to query multiple tables at once in a single request. In GraphQL, only the information requested will be returned which can be contrasted to REST APIs. In the example below, this query will return the name of all `interfaces` attached to the device `nyc-sw01` along with all `ip_addresses` attached to those interfaces.

```graphql
query {
  devices(name: "nyc-sw01") {
    name
    interfaces {
      name
      ip_addresses {
        address
      }
    }
  }
}
```

Result

```json
{
  "data": {
    "devices": [
      {
        "name": "nyc-sw01",
        "interfaces": [
          {
            "name": "xe-0/0/0",
            "ip_addresses": [
              {
                "address": "10.52.0.1/30"
              }
            ]
          },
          {
            "name": "xe-0/0/1",
            "ip_addresses": []
          }
        ]
      }
    ]
  }
}
```

It is possible to explore the Graph and create some queries in a human friendly UI at the endpoint `graphql/`. This interface (called `graphqli`) provides a great playground to build new queries as it provides full autocompletion and type validation.

## Querying the GraphQL interface over the rest API

It is possible to query the GraphQL interface via the rest API as well, the endpoint is available at `api/graphql/` and supports the same Token based authentication as all other Nautobot APIs.

A GraphQL Query must be encapsulated in a JSON payload with the `query` key and sent with a POST request. Optionally it is possible to provide a list of `variables` in the same payload as presented below.

```json
{
  "query": "query ($id: Int!) { device(id: $id) { name }}",
  "variables": { "id": 3}
}
```

## Working with Custom Fields

GraphQL custom fields data data is provided in two formats, a "greedy" and a "prefixed" format. The greedy format provides all custom field data associated with this record under a single "custom_field_data" key. This is helpful in situations where custom fields are likely to be added at a later date, the data will simply be added to the same root key and immediately accessible without the need to adjust the query.

```graphql
query {
  sites {
    name
    custom_field_data
  }
}
```

Result

```json
{
  "data": {
    "sites": [
      {
        "name": "nyc-site-01",
        "custom_field_data": {
          "site_type": "large"
        }
      },
      {
        "name": "nyc-site-02",
        "custom_field_data": {
          "site_type": "small"
        }
      }
    ]
  }
}
```

Additionally, by default, all custom fields in GraphQL will be prefixed with `cf_`. A custom field name `site_type` will appear in GraphQL as `cf_site_type` as an example. The prefix can be changed by setting the value of [`GRAPHQL_CUSTOM_FIELD_PREFIX`](../configuration/optional-settings.md#graphql_custom_field_prefix).

```graphql
query {
  sites {
    name
    cf_site_type
  }
}
```

Result

```json
{
  "data": {
    "sites": [
      {
        "name": "nyc-site-01",
        "cf_site_type": "large"
      },
      {
        "name": "nyc-site-02",
        "cf_site_type": "small"
      }
    ]
  }
}
```

!!! important
    Custom Fields with the prefixed `cf_` are only available in GraphQL **after** the custom field is created **and** the web service is restarted.

## Working with Relationships

Defined [relationships](../models/extras/relationship.md) are available in GraphQL as well. In most cases, the associated objects for a given relationship will be available under the key `rel_<relationship_slug>`. The one exception is for relationships between objects of the same type that are not defined as symmetric; for these relationships it's important to be able to distinguish between the two "sides" of the relationship, and so the associated objects will be available under `rel_<relationship_slug>_source` and/or `rel_<relationship_slug>_destination` as appropriate.

!!! important
    Relationships are only available in GraphQL **after** the relationship is created **and** the web service is restarted.

```graphql
query {
  ip_addresses {
    address
    rel_peer_address {
      address
    }
    rel_parent_child_source {
      address
    }
    rel_parent_child_destination {
      address
    }
  }
}
```

Result

```json
{
  "data": {
    "ip_addresses": [
      {
        "address": "10.1.1.1/24",
        "rel_peer_address": {
          "address": "10.1.1.2/24"
        },
        "rel_parent_child_source": null,
        "rel_parent_child_destination": [
          {
            "address": "10.1.1.1/30"
          },
          {
            "address": "10.1.1.1/32"
          }
        ]
      },
      {
        "address": "10.1.1.1/30",
        "rel_peer_address": null,
        "rel_parent_child_source": {
          "address": "10.1.1.1/24"
        },
        "rel_parent_child_destination": []
      },
      {
        "address": "10.1.1.1/32",
        "rel_peer_address": null,
        "rel_parent_child_source": {
          "address": "10.1.1.1/24"
        },
        "rel_parent_child_destination": []
      },
      {
        "address": "10.1.1.2/24",
        "rel_peer_address": {
          "address": "10.1.1.1/24"
        },
        "rel_parent_child_source": null,
        "rel_parent_child_destination": []
      }
    ]
  }
}
```

## Working with Computed Fields

By default, all custom fields in GraphQL will be prefixed with `cpf_`. A computed field name `ip_ptr_record` will appear in GraphQL as `cpf_ip_ptr_record` as an example. The prefix can be changed by setting the value of [`GRAPHQL_COMPUTED_FIELD_PREFIX`](../configuration/optional-settings.md#graphql_computed_field_prefix).

```graphql
{
  ip_addresses {
    address
    dns_name
    cpf_ip_ptr_record
  }
}
```

Result

```json
{
  "data": {
    "ip_addresses": [
      {
        "address": "10.0.0.0/32",
        "dns_name": "ip-10-0-0-0.server.atl01.atc.nautobot.com",
        "cpf_ip_ptr_record": "0.0.0.10.in-addr.arpa"
      },
      {
        "address": "10.0.1.0/32",
        "dns_name": "ip-10-0-1-0.server.atl01.atc.nautobot.com",
        "cpf_ip_ptr_record": "0.1.0.10.in-addr.arpa"
      }
    ]
  }
}
```

!!! important
    Computed Fields with the prefixed `cpf_` are only available in GraphQL **after** the computed field is created **and** the web service is restarted.

## Saved Queries

+++ 1.1.0

Queries can now be stored inside of Nautobot, allowing the user to easily rerun previously defined queries.

Inside of **Extensibility -> Data Management -> GraphQL Queries**, there are views to create and manage GraphQL queries.

Saved queries can be executed from the detailed query view or via a REST API request. The queries can also be populated from the detailed query view into GraphiQL by using the "Open in GraphiQL" button. Additionally, in the GraphiQL UI, there is now a menu item, "Queries", which can be used to populate GraphiQL with any previously saved query.

To execute a stored query via the REST API, a POST request can be sent to `/api/extras/graphql-queries/[slug]/run/`. Any GraphQL variables required by the query can be passed in as JSON data within the request body.
