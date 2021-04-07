# GraphQL User Guide

## Introduction

### What is GraphQL?

GraphQL is a query language for your APIs and a runtime for fulfilling those queries with your existing data.<sup>(1)</sup>

### How GraphQL simplifies API Interactions

When interacting with APIs, It's often necessary to build relationships between multiple models to achieve the result that is desired. Doing this typically requires multiple API calls to create the relationships. For example, lets assume that there are two devices in Nautobot. Each are assigned a site, region, roles, interfaces, and IP Addresses.

Simply querying the `/api/dcim/devices/` API route provides:
<div>
  <details>
    <summary>View API Results</summary>
```
{
  "count": 208,
  "next": "https://demo.nautobot.com/api/dcim/devices/?limit=1&offset=2",
  "previous": "https://demo.nautobot.com/api/dcim/devices/?limit=1",
  "results": [
    {
      "id": "c8886c88-6eff-4c4f-a079-4ef16b53d4f6",
      "url": "https://demo.nautobot.com/api/dcim/devices/c8886c88-6eff-4c4f-a079-4ef16b53d4f6/",
      "name": "ams-edge-02",
      "display_name": "ams-edge-02",
      "device_type": {
        "id": "244ea351-3c7a-4d23-ba80-5db6b65312cc",
        "url": "https://demo.nautobot.com/api/dcim/device-types/244ea351-3c7a-4d23-ba80-5db6b65312cc/",
        "manufacturer": {
          "id": "687f53d9-2c51-40fd-83aa-875e43d01a05",
          "url": "https://demo.nautobot.com/api/dcim/manufacturers/687f53d9-2c51-40fd-83aa-875e43d01a05/",
          "name": "Arista",
          "slug": "arista"
        },
        "model": "DCS-7280CR2-60",
        "slug": "dcs-7280cr2-60",
        "display_name": "Arista DCS-7280CR2-60"
      },
      "device_role": {
        "id": "a3637471-6b4d-4f5a-a249-838d621abe60",
        "url": "https://demo.nautobot.com/api/dcim/device-roles/a3637471-6b4d-4f5a-a249-838d621abe60/",
        "name": "edge",
        "slug": "edge"
      },
      "tenant": null,
      "platform": null,
      "serial": "",
      "asset_tag": null,
      "site": {
        "id": "4ad439e9-4f1b-41c9-bc8c-dd7c1c921dc3",
        "url": "https://demo.nautobot.com/api/dcim/sites/4ad439e9-4f1b-41c9-bc8c-dd7c1c921dc3/",
        "name": "ams",
        "slug": "ams"
      },
      "rack": {
        "id": "bff3f7af-bd77-49b6-a57a-9c4b8fc7673a",
        "url": "https://demo.nautobot.com/api/dcim/racks/bff3f7af-bd77-49b6-a57a-9c4b8fc7673a/",
        "name": "ams-102",
        "display_name": "ams-102"
      },
      "position": 40,
      "face": {
        "value": "front",
        "label": "Front"
      },
      "parent_device": null,
      "status": {
        "value": "active",
        "label": "Active"
      },
      "primary_ip": null,
      "primary_ip4": null,
      "primary_ip6": null,
      "cluster": null,
      "virtual_chassis": null,
      "vc_position": null,
      "vc_priority": null,
      "comments": "",
      "local_context_data": null,
      "tags": [],
      "custom_fields": {},
      "config_context": {
        "cdp": true,
        "ntp": [
          {
            "ip": "10.1.1.1",
            "prefer": false
          },
          {
            "ip": "10.2.2.2",
            "prefer": true
          }
        ],
        "lldp": true,
        "snmp": {
          "host": [
            {
              "ip": "10.1.1.1",
              "version": "2c",
              "community": "networktocode"
            }
          ],
          "contact": "John Smith",
          "location": "Network to Code - NYC | NY",
          "community": [
            {
              "name": "ntc-public",
              "role": "RO"
            },
            {
              "name": "ntc-private",
              "role": "RW"
            },
            {
              "name": "networktocode",
              "role": "RO"
            },
            {
              "name": "secure",
              "role": "RW"
            }
          ]
        },
        "aaa-new-model": false,
        "acl": {
          "definitions": {
            "named": {
              "PERMIT_ROUTES": [
                "10 permit ip any any"
              ]
            }
          }
        },
        "route-maps": {
          "PERMIT_CONN_ROUTES": {
            "seq": 10,
            "type": "permit",
            "statements": [
              "match ip address PERMIT_ROUTES"
            ]
          }
        }
      },
      "created": "2021-02-25",
      "last_updated": "2021-02-25T14:51:57.609598"
    }
  ]
}
```
  </details>
</div>

<br />
There is a lot of useful information in that API call, but there is also a lot of information that is missing; such as interfaces and ip addresses associated with the devices. There is also potentially a lot of information that isn't needed for the specific task. To retrieve the missing information, subsequent API calls would need to be performed; and those API results would need to be correlated to the correct device.

GraphQL reduces the complexity of performing multiple API calls and correlating results by empowering the user to create their own query that provides the user exactly what they want and nothing that they don't, in a single API call.

### Exploring GraphQL in Nautobot

In Nautobot, there is a link to the GraphQL web interface at the bottom right-hand side of the page. The GraphQL web interface is called GraphiQL. Navigating to the URI (`/graphql`), brings up the GraphiQL tool for creating queries. This interface is useful for exploring the possibilities of GraphQL and validating that written queries execute successfully.

![GraphiQL Interface](/guides/images/graphql/graphiql.png)

### Documentation Explorer

If you're new to GraphQL, take a little bit of time to explore the *Documentation Explorer*. This can be accomplished by clicking the `< Docs` link in the GraphiQL interface. The information within *Documentation Explorer* is specific to creating queries in Nautobot.

![Documentation Explorer](/guides/images/graphql/graphiql-explorer.png)

In the *Documentation Explorer*, search for `devices`. The results are all of the models that utilize the `devices` model.

![Documentation Explorer - devices](/guides/images/graphql/graphiql-explorer-device-query.png)

From the `devices` query, select `devices` from `Query.devices`. This will display all of the potential query fields from devices.

![Documentation Explorer - device fields](/guides/images/graphql/graphiql-explorer-device-attributes.png)

### First Query

Now that you have a basic understanding of how to obtain information to query from the *Documentation Explorer*, let's craft a query. Earlier in the guide, a sample REST API call was performed to obtain device information. While the query had a lot of important information, it also lacked a lot of information. In this section, lets explore how to craft a GraphQL query that displays all of the information that we want.

GraphQL queries are encapsulated in `query { }` flags. In recent iterations of GraphQL, `{ }` is also acceptable. With that in mind, lets craft our query. From the GraphiQL interfaces, lets query for all devices and display their device names. To do this, let's execute:

```
query {
  devices {
    name
  }
}
```

This query will retrieve a list of all devices by their hostname.
<div>
  <details>
    <summary>View GraphQL Query Results</summary>
    <img src="/guides/images/graphql/graphql-query-01.png">
  </details>
</div>

<br />
Now, let's modify the query to provide interface names for each device. We can do that by modifying the existing query to add `interfaces { name }` as a sub-query of `devices`. GraphiQL makes this process a bit easier, because it has syntax completion built in.

![GraphiQL - Autocompletion](/guides/images/graphql/graphiql-autocomplete.png)

```
query {
  devices {
    name
    interfaces {
      name
    }
  }
}
```

The result is a list of all the devices by their hostname and associated interfaces by their names.
<div>
  <details>
    <summary>View GraphQL Query Results</summary>
    <img src="/guides/images/graphql/graphql-query-02.png">
  </details>
</div>

<br />
We can continue iterating on the query until we get exactly what we want from the query. For example, if I wanted to iterate on the previous query to not only display the interfaces of the devices, but also display the interface description, the IP Addresses associated with the interface, and whether or not the interface was a dedicated management interface; I would structure the query like:

```
query {
  devices {
    name
    interfaces {
      name
      description
      mgmt_only
      ip_addresses {
        address
      }   
    }
  }
}
```

The results of the query look like:
<div>
  <details>
    <summary>View GraphQL Query Results</summary>
    <img src="/guides/images/graphql/graphql-query-03.png">
  </details>
</div>

<br />

### Filtering Queries

These queries are great, but they are displaying the interface attributes and device names for every device in the Nautobot inventory. Currently, Nautobot allows users to filter queries at the top level of the query. In our previous examples, the top level would be the `devices` query.

As an example. We can query devices by their site location. This is done by adding `(site: "<site name>")` after `devices`. For example: `query { devices(site: "ams") { name }}` will display all devices in the `ams` site.
<div>
  <details>
    <summary>View GraphQL Query Results</summary>
    <img src="/guides/images/graphql/graphql-query-04.png">
  </details>
</div>

<br />
GraphiQL allows you to add multiple attributes to the filter criteria. You can use the *Documentation Explorer* to assist you in finding criteria attributes to filter on. In this example, I add the `role` attribute in addition to `site`. 

```
query {
  devices(site:"ams", role: "edge") {
    name
  }
}
```
<div>
  <details>
    <summary>View GraphQL Query Results</summary>
    <img src="/guides/images/graphql/graphql-query-05.png">
  </details>
</div>

<br />
## Using the GraphQL API in Nautobot

Now that we've explored how to use the GraphiQL interface to help us create GraphQL queries, let's take our queries and call them with the REST API. This is where the real advantage is going to come in to play, because it will allow us to utilize these queries in a programmatic way.

![Swagger - GraphQL](/guides/images/graphql/graphql-swagger.png)

From the [Nautobot Swagger documentation](https://demo.nautobot.com/api/docs/), we can see that the API calls to `/api/graphql` require a HTTP POST method. In the HTTP POST, the `query` field is a required. The `query` field is where we put the GraphQL query. The `variables` field is optional. It's where we define filters, if we choose to do so. 

To simplify the process even more, we'll utilize the [PyNautobot SDK](https://pynautobot.readthedocs.io/en/latest/index.html).

Here is an example Python script using the `PyNautobot SDK` to query GraphQL:

```python
#!/usr/bin/env python3

import pynautobot
import json

query = """
query {
  devices {
    name
    interfaces {
      name
      description
      mgmt_only
      ip_addresses {
        address
      }
    }
  }
}
"""
nb = pynautobot.api(
    url="http://localhost",
    token="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)
gql = nb.graphql.query(query=query)

print(json.dumps(gql.json, indent=2))
```

The contents of the `query` variable was taken directly from the example above where we grabbed all device interfaces and associated attributes. We then take the output and print the contents as a JSON object. Now, let's iterate on the script to filter the contents with the `variable` flag. Just as we did above, we'll filter by `site`.

```python
#!/usr/bin/env python3

import pynautobot
import json

variables = {"site_name": "ams"}
query = """
query ($site_name:String!) {
  devices (site: $site_name) {
    name
    interfaces {
      name
      mgmt_only
      ip_addresses {
        address
      }
    }
  }
}
"""
nb = pynautobot.api(
    url="http://localhost",
    token="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)
gql = nb.graphql.query(query=query, variables=variables)

print(json.dumps(gql.json, indent=2))
```

In the updated script, we add the `variables = {"site_name": "ams"}` variable. We then update the query to let GraphQL know that we will be sending parameters to to filter by `site`. The updated output is still a JSON object. Instead of fetching all devices, we are filtering by devices in the `ams` site. The `PyNautobot SDK` has some excellent GraphQL [examples](https://pynautobot.readthedocs.io/en/latest/api/core/graphql.html). Be sure to check out the documentation.

## Closing

GraphQL is a powerful, yet simple, tool for querying the exact information that is necessary for the task at hand. For further information about GraphQL, be sure to check out the [GraphQL Docs](https://graphql.org/learn/)!

## Citations
> 1. *Article Title: GraphQL, URL: https://graphql.org/, Website Title: GraphQL, Date Accessed: March 8, 2021*
