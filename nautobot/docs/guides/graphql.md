# GraphQL User Guide

## Introduction

## What is GraphQL?

GraphQL is a query language for your APIs and a runtime for fulfilling those queries with your existing data.<sup>(1)</sup>

## How GraphQL simplifies API Interactions

When interacting with APIs, It's often necessary to build relationships between multiple models to achieve the result that is desired. Doing this typically requires multiple API calls to create the relationships that are desired. For example, lets assume that there are two devices in Nautobot. Each are assigned a site, region, roles, interfaces, and IP Addresses.

Simply querying the `/api/dcim/devices/` API route provides:

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
There is a lot of useful information in that API call, but there is also a lot of information that is missing; such as interfaces and ip addresses associated with the devices. There is also potentially a lot of information that isn't needed for the specific task. To retrieve the missing information, subsequent API calls would need to be performed; and those API results would need to be correlated to the correct device.

GraphQL reduces the complexity of performing multiple API calls and correlating results by empowering the user to create their own query that provides the user exactly what they want and nothing that they don't, in a single API call.

## Exploring GraphQL in Nautobot

In Nautobot, there is a link to the Graph*i*QL interface at the bottom right-hand side of the page. Navigating to the page (`/graphql`), brings up the Graph*i*QL tool for creating queries. This interface is useful for exploring the possibilities of GraphQL and validating that written queries execute successfully.

![Graph*i*QL Interface](/guides/images/graphql/graphiql-01.png)

### Documentation Explorer

If you're new to GraphQL, take a little bit of time to explore the `Documentation Explorer`. This can be accomplished by clicking the `< Docs` link in the Graph*i*QL interface. The information within `Documentation Explorer` is specific to creating queries in `Nautobot`.

![Documentation Explorer](/guides/images/graphql/graphiql-02.png)

In the `Documentation Explorer`, search for `devices`. The results are all of the models that utilize the `devices` model.

![Documentation Explorer - devices](/guides/images/graphql/graphiql-03.png)

From the `devices` query, select `devices` from `Query.devices`. This will display all of the potential query fields from devices.

![Documentation Explorer - device fields](/guides/images/graphql/graphiql-04.png)

### First Query

Now that you have a basic understanding of how to obtain information to query from the `Documentation Explorer`, let's craft a query. Earlier in the guide, a sample RestAPI call was performed to obtain device information. While the query had a lot of important information, it also lacked a lot of information. In this section, lets explore how to craft a GraphQL query that displays all of the information that we want.

GraphQL queries are encapsulated in `query { }` flags. In recent iterations of GraphQL, `{ }` is also acceptable. With that in mind, lets craft our query. From the Graph*i*QL interfaces, lets query for all devices and display their device names. To do this, let's execute:

```
query {
  devices {
    name
  }
}
```

This query will retrieve a list of all devices by their hostname.

```
{
  "data": {
    "devices": [
      {
        "name": "ams-edge-01"
      },
      {
        "name": "ams-edge-02"
      },
      {
        "name": "ams-leaf-01"
      },
      {
        "name": "ams-leaf-02"
      },
      {
        "name": "ams-leaf-03"
      },
      {
        "name": "ams-leaf-04"
      },
      {
        "name": "ams-leaf-05"
      },
      {
        "name": "ams-leaf-06"
      },
      {
        "name": "ams-leaf-07"
      },
      {
        "name": "ams-leaf-08"
      },
      {
        "name": "atl-edge-01"
      },
      {
        "name": "atl-edge-02"
      },
      {
        "name": "atl-leaf-01"
      },
      {
        "name": "atl-leaf-02"
      },
      {
        "name": "atl-leaf-03"
      },
      {
        "name": "atl-leaf-04"
      },
      {
        "name": "atl-leaf-05"
      },
      {
        "name": "atl-leaf-06"
      },
      {
        "name": "atl-leaf-07"
      },
      {
        "name": "atl-leaf-08"
      },
      {
        "name": "bkk-edge-01"
      },
      {
        "name": "bkk-edge-02"
      },
      {
        "name": "bkk-leaf-01"
      },
      {
        "name": "bkk-leaf-02"
      },
      {
        "name": "bkk-leaf-03"
      },
      {
        "name": "bkk-leaf-04"
      },
      {
        "name": "bkk-leaf-05"
      },
      {
        "name": "bkk-leaf-06"
      },
      {
        "name": "bkk-leaf-07"
      },
      {
        "name": "bkk-leaf-08"
      },
      {
        "name": "can-edge-01"
      },
      {
        "name": "can-edge-02"
      },
      {
        "name": "can-leaf-01"
      },
      {
        "name": "can-leaf-02"
      },
      {
        "name": "can-leaf-03"
      },
      {
        "name": "can-leaf-04"
      },
      {
        "name": "can-leaf-05"
      },
      {
        "name": "can-leaf-06"
      },
      {
        "name": "can-leaf-07"
      },
      {
        "name": "can-leaf-08"
      },
      {
        "name": "cdg-edge-01"
      },
      {
        "name": "cdg-edge-02"
      },
      {
        "name": "cdg-leaf-01"
      },
      {
        "name": "cdg-leaf-02"
      },
      {
        "name": "cdg-leaf-03"
      },
      {
        "name": "cdg-leaf-04"
      },
      {
        "name": "cdg-leaf-05"
      },
      {
        "name": "cdg-leaf-06"
      },
      {
        "name": "cdg-leaf-07"
      },
      {
        "name": "cdg-leaf-08"
      },
      {
        "name": "del-edge-01"
      },
      {
        "name": "del-edge-02"
      },
      {
        "name": "del-leaf-01"
      },
      {
        "name": "del-leaf-02"
      },
      {
        "name": "del-leaf-03"
      },
      {
        "name": "del-leaf-04"
      },
      {
        "name": "del-leaf-05"
      },
      {
        "name": "del-leaf-06"
      },
      {
        "name": "del-leaf-07"
      },
      {
        "name": "del-leaf-08"
      },
      {
        "name": "del-leaf-09"
      },
      {
        "name": "del-leaf-10"
      },
      {
        "name": "den-edge-01"
      },
      {
        "name": "den-edge-02"
      },
      {
        "name": "den-leaf-01"
      },
      {
        "name": "den-leaf-02"
      },
      {
        "name": "den-leaf-03"
      },
      {
        "name": "den-leaf-04"
      },
      {
        "name": "den-leaf-05"
      },
      {
        "name": "den-leaf-06"
      },
      {
        "name": "den-leaf-07"
      },
      {
        "name": "den-leaf-08"
      },
      {
        "name": "dfw-edge-01"
      },
      {
        "name": "dfw-edge-02"
      },
      {
        "name": "dfw-leaf-01"
      },
      {
        "name": "dfw-leaf-02"
      },
      {
        "name": "dfw-leaf-03"
      },
      {
        "name": "dfw-leaf-04"
      },
      {
        "name": "dfw-leaf-05"
      },
      {
        "name": "dfw-leaf-06"
      },
      {
        "name": "dfw-leaf-07"
      },
      {
        "name": "dfw-leaf-08"
      },
      {
        "name": "dxb-edge-01"
      },
      {
        "name": "dxb-edge-02"
      },
      {
        "name": "dxb-leaf-01"
      },
      {
        "name": "dxb-leaf-02"
      },
      {
        "name": "dxb-leaf-03"
      },
      {
        "name": "dxb-leaf-04"
      },
      {
        "name": "dxb-leaf-05"
      },
      {
        "name": "dxb-leaf-06"
      },
      {
        "name": "dxb-leaf-07"
      },
      {
        "name": "dxb-leaf-08"
      },
      {
        "name": "fra-edge-01"
      },
      {
        "name": "fra-edge-02"
      },
      {
        "name": "fra-leaf-01"
      },
      {
        "name": "fra-leaf-02"
      },
      {
        "name": "fra-leaf-03"
      },
      {
        "name": "fra-leaf-04"
      },
      {
        "name": "fra-leaf-05"
      },
      {
        "name": "fra-leaf-06"
      },
      {
        "name": "fra-leaf-07"
      },
      {
        "name": "fra-leaf-08"
      },
      {
        "name": "hkg-edge-01"
      },
      {
        "name": "hkg-edge-02"
      },
      {
        "name": "hkg-leaf-01"
      },
      {
        "name": "hkg-leaf-02"
      },
      {
        "name": "hkg-leaf-03"
      },
      {
        "name": "hkg-leaf-04"
      },
      {
        "name": "hkg-leaf-05"
      },
      {
        "name": "hkg-leaf-06"
      },
      {
        "name": "hkg-leaf-07"
      },
      {
        "name": "hkg-leaf-08"
      },
      {
        "name": "hnd-edge-01"
      },
      {
        "name": "hnd-edge-02"
      },
      {
        "name": "hnd-leaf-01"
      },
      {
        "name": "hnd-leaf-02"
      },
      {
        "name": "hnd-leaf-03"
      },
      {
        "name": "hnd-leaf-04"
      },
      {
        "name": "hnd-leaf-05"
      },
      {
        "name": "hnd-leaf-06"
      },
      {
        "name": "hnd-leaf-07"
      },
      {
        "name": "hnd-leaf-08"
      },
      {
        "name": "icn-edge-01"
      },
      {
        "name": "icn-edge-02"
      },
      {
        "name": "icn-leaf-01"
      },
      {
        "name": "icn-leaf-02"
      },
      {
        "name": "icn-leaf-03"
      },
      {
        "name": "icn-leaf-04"
      },
      {
        "name": "jcy-bb-01.infra.ntc.com"
      },
      {
        "name": "jcy-rtr-01.infra.ntc.com"
      },
      {
        "name": "jcy-rtr-02.infra.ntc.com"
      },
      {
        "name": "jcy-spine-01.infra.ntc.com"
      },
      {
        "name": "jcy-spine-02.infra.ntc.com"
      },
      {
        "name": "jfk-edge-01"
      },
      {
        "name": "jfk-edge-02"
      },
      {
        "name": "jfk-leaf-01"
      },
      {
        "name": "jfk-leaf-02"
      },
      {
        "name": "jfk-leaf-03"
      },
      {
        "name": "jfk-leaf-04"
      },
      {
        "name": "jfk-leaf-05"
      },
      {
        "name": "jfk-leaf-06"
      },
      {
        "name": "jfk-leaf-07"
      },
      {
        "name": "jfk-leaf-08"
      },
      {
        "name": "lax-edge-01"
      },
      {
        "name": "lax-edge-02"
      },
      {
        "name": "lax-leaf-01"
      },
      {
        "name": "lax-leaf-02"
      },
      {
        "name": "lax-leaf-03"
      },
      {
        "name": "lax-leaf-04"
      },
      {
        "name": "lax-leaf-05"
      },
      {
        "name": "lax-leaf-06"
      },
      {
        "name": "lax-leaf-07"
      },
      {
        "name": "lax-leaf-08"
      },
      {
        "name": "lax-leaf-09"
      },
      {
        "name": "lax-leaf-10"
      },
      {
        "name": "lhr-edge-01"
      },
      {
        "name": "lhr-edge-02"
      },
      {
        "name": "lhr-leaf-01"
      },
      {
        "name": "lhr-leaf-02"
      },
      {
        "name": "lhr-leaf-03"
      },
      {
        "name": "lhr-leaf-04"
      },
      {
        "name": "lhr-leaf-05"
      },
      {
        "name": "lhr-leaf-06"
      },
      {
        "name": "lhr-leaf-07"
      },
      {
        "name": "lhr-leaf-08"
      },
      {
        "name": "nyc-bb-01.infra.ntc.com"
      },
      {
        "name": "nyc-leaf-01.infra.ntc.com"
      },
      {
        "name": "nyc-leaf-02.infra.ntc.com"
      },
      {
        "name": "nyc-rtr-01.infra.ntc.com"
      },
      {
        "name": "nyc-rtr-02.infra.ntc.com"
      },
      {
        "name": "nyc-spine-01.infra.ntc.com"
      },
      {
        "name": "nyc-spine-02.infra.ntc.com"
      },
      {
        "name": "ord-edge-01"
      },
      {
        "name": "ord-edge-02"
      },
      {
        "name": "ord-leaf-01"
      },
      {
        "name": "ord-leaf-02"
      },
      {
        "name": "ord-leaf-03"
      },
      {
        "name": "ord-leaf-04"
      },
      {
        "name": "ord-leaf-05"
      },
      {
        "name": "ord-leaf-06"
      },
      {
        "name": "ord-leaf-07"
      },
      {
        "name": "ord-leaf-08"
      },
      {
        "name": "pek-edge-01"
      },
      {
        "name": "pek-edge-02"
      },
      {
        "name": "pek-leaf-01"
      },
      {
        "name": "pek-leaf-02"
      },
      {
        "name": "pek-leaf-03"
      },
      {
        "name": "pek-leaf-04"
      },
      {
        "name": "pek-leaf-05"
      },
      {
        "name": "pek-leaf-06"
      },
      {
        "name": "pek-leaf-07"
      },
      {
        "name": "pek-leaf-08"
      },
      {
        "name": "pvg-edge-01"
      },
      {
        "name": "pvg-edge-02"
      },
      {
        "name": "pvg-leaf-01"
      },
      {
        "name": "pvg-leaf-02"
      },
      {
        "name": "pvg-leaf-03"
      },
      {
        "name": "pvg-leaf-04"
      },
      {
        "name": "sin-edge-01"
      },
      {
        "name": "sin-edge-02"
      },
      {
        "name": "sin-leaf-01"
      },
      {
        "name": "sin-leaf-02"
      },
      {
        "name": "sin-leaf-03"
      },
      {
        "name": "sin-leaf-04"
      },
      {
        "name": "sin-leaf-05"
      },
      {
        "name": "sin-leaf-06"
      },
      {
        "name": "sin-leaf-07"
      },
      {
        "name": "sin-leaf-08"
      }
    ]
  }
}
```

Now, let's modify the query to provide interface names for each device. We can do that by modifying the existing query to add `interfaces { name }` as a sub-query of `devices`. Graph*i*QL makes this process a bit easier, because it has syntax completion built in.

![Graph*i*QL - Autocompletion](/guides/images/graphql/graphiql-05.png)

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

![Graph*i*QL - Simple Query 1](/guides/images/graphql/graphiql-06.png)

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

![Graph*i*QL - Simple Query 2](/guides/images/graphql/graphiql-07.png)

### Filtering Queries

These queries are great, but they are displaying the interface attributes and device names for every device in the Nautobot inventory. Currently, Nautobot allows users to filter queries at the top level of the query. In our previous examples, the top level would be the `devices` query.

As an example. We can query devices by their site location. This is done by added `(site: "<site name>")` after devices. For example: `query { devices(site: "ams") { name }}` will display all devices in the `ams` site.

```
{
  "data": {
    "devices": [
      {
        "name": "ams-edge-01"
      },
      {
        "name": "ams-edge-02"
      },
      {
        "name": "ams-leaf-01"
      },
      {
        "name": "ams-leaf-02"
      },
      {
        "name": "ams-leaf-03"
      },
      {
        "name": "ams-leaf-04"
      },
      {
        "name": "ams-leaf-05"
      },
      {
        "name": "ams-leaf-06"
      },
      {
        "name": "ams-leaf-07"
      },
      {
        "name": "ams-leaf-08"
      }
    ]
  }
}
```

Graph*i*QL allows you to add multiple attributes to the filter criteria. You can use the `Documentation Explorer` to assist you in finding criteria attributes to filte on. In this example, I add the `manufacturer` attribute in addition to `site`. 

```
query {
  devices(site:"ams", manufacturer: "Arista") {
    name
  }
}
```

```
{
  "data": {
    "devices": [
      {
        "name": "ams-edge-01"
      },
      {
        "name": "ams-edge-02"
      },
      {
        "name": "ams-leaf-01"
      },
      {
        "name": "ams-leaf-02"
      },
      {
        "name": "ams-leaf-03"
      },
      {
        "name": "ams-leaf-04"
      },
      {
        "name": "ams-leaf-05"
      },
      {
        "name": "ams-leaf-06"
      },
      {
        "name": "ams-leaf-07"
      },
      {
        "name": "ams-leaf-08"
      }
    ]
  }
}
```

## Using the GraphQL API in Nautobot

Now that we've explored how to use the Graph*i*QL interface to help us create GraphQL queries, let's take our queries and call them with the Rest API. This is where the real advantage is going to come in to play, because it will allow us to utilize these queries in a programmatic way.

![Swagger - GraphQL](/guides/images/graphql/graphql-swagger-01.png)

From the [Nautobot Swagger documentation](https://demo.nautobot.com/api/docs/), we can see that the API calls to `/api/graphql` require a HTTP POST method. In the HTTP POST, the `query` field is a required. The `query` field is where we put the GraphQL query. The `variables` field is optional. It's where we define filters, if we choose to do so. 

To simplify the process even more, we'll utilize the [PyNautobot SDK](https://pynautobot.readthedocs.io/en/latest/index.html).

Here is an example Python script using the `PyNautobot SDK` to query GraphQL:

```python
#!/usr/bin/env python3

import pynautobot
import json


nb = pynautobot.api(
    url="http://localhost",
    token="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)
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
gql = nb.graphql.query(query=query)

print(json.dumps(gql.json, indent=2))
```

The contents of the `query` variable was taken directly from the example above where we grabbed all device interfaces and associated attributes. We then take the output and print the contents as a JSON object. Now, let's iterate on the script to filter the contents with the `variable` flag. Just as we did above, we'll filter by `site`.

```python
#!/usr/bin/env python3

import pynautobot
import json


nb = pynautobot.api(
    url="http://localhost",
    token="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)
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
gql = nb.graphql.query(query=query, variables=variables)

print(json.dumps(gql.json, indent=2))
```

In the updated script, we add the `variables = {"site_name": "ams"}` variable. We then update the query to let GraphQL know that we will be sending parameters to to filter by `site`. The updated output is still a JSON object. instead of fetching all devices, we are filtering by devices in the `ams` site. The `PyNautobot SDK` has some excellent GraphQL [examples](https://pynautobot.readthedocs.io/en/latest/api/core/graphql.html). Be sure to check out the documentation.

## Closing

GraphQL is a powerful, yet simple, tool for querying the exact information that is necessary for the task at hand. For further information about GraphQL, be sure to check out the [GraphQL Docs](https://graphql.org/learn/)!

## Citations
> 1. *Article Title: GraphQL, URL: https://graphql.org/, Website Title: GraphQL, Date Accessed: March 8, 2021*
