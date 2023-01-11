# Device Redundancy Groups

+++ 1.5.0

Device Redundancy Groups represent logical relationships between multiple devices. Typically, a redundancy group could represent a failover pair, failover group, or a load sharing cluster.
Device Redundancy Groups are created first, before the devices are assigned to the group.

A failover strategy represents intended operation mode of the group. Supported failover strategy are: Active/Active and Active/Standby.

Secrets groups could be used to inform store secret information used by failover or a cluster of devices.

Device Redundancy Group Priority is a Device attribute defined during assigning a Device to a Device Redundancy Group. This field represents the priority the device has in the device redundancy group.

## Example use of Device Redundancy Groups - Cisco ASA 5500 Series Active/Standby Failover

This document provides an example of generating a Cisco ASA device's desired failover configuration based on data stored in Nautobot Device Redundancy Groups.
A GraphQL query is used to retrieve the relevant data, which is then rendered through a Jinja2 template to produce the desired configuration.

As one of the use cases for Device Redundacy Groups, introduced in Nautobot 1.5 release, is to model failover pairs, we will use the ASA 5500 Series in this example with details as follows:

* Firewall failover pair is composed of two devices named "nyc-fw-primary" and "nyc-fw-secondary"
* Each firewall device forming a failover cluster has a virtual interface dedicated for failover usage (named "failover-link") and addressed in 172.27.48.0/31 network
* Virtual failover interface has a physical parent interface assigned ("gigabitethernet0/3")
* Following redundancy group priorities are assigned in a failover pair:
    * Priority 100 for a Primary Failover unit
    * Priority 50 for a Secondary Failover unit

### Querying for the data

To retrieve information about devices forming an ASA Failover pair, we will use a GraphQL query and the `get_gql_failover_details` Python method.
This method takes a `device_name` as an argument.

```python
import json
import pynautobot

query = """
query ($device_name: [String]) {
    devices(name__ie: $device_name) {
        name
        device_redundancy_group {
            name
            members {
                name
                device_redundancy_group_priority
                interfaces(name__ie: "failover-link") {
                    type
                    name
                    ip_addresses {
                        host
                        prefix_length
                    }
                    parent_interface {
                        name
                        type
                    }
                }
            }
        }
    }
}
"""

def get_gql_failover_details(device_name):
    variables = {"device_name": device_name}
    nb = pynautobot.api(
        url="http://localhost:8080",
        token="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    return nb.graphql.query(query=query, variables=variables)
```

### Retrieving the data - Primary Failover Unit ("nyc-fw-primary")

We will demonstrate how to execute the command for Primary Unit only, however you could repeat the process for a secondary unit. An example data returned from Nautobot is presented below.

```python
>>> hostname = "nyc-fw-primary"
>>> gql_data = get_gql_failover_details(hostname).json
```

```json
{
    "data": {
        "devices": [
            {
                "name": "nyc-fw-primary",
                "device_redundancy_group": {
                    "name": "nyc-firewalls",
                    "members": [
                        {
                            "name": "nyc-fw-primary",
                            "device_redundancy_group_priority": 100,
                            "interfaces": [
                                {
                                    "type": "VIRTUAL",
                                    "name": "failover-link",
                                    "ip_addresses": [
                                        {
                                            "host": "172.27.48.0",
                                            "prefix_length": 31
                                        }
                                    ],
                                    "parent_interface": {
                                        "name": "gigabitethernet0/3",
                                        "type": "A_1000BASE_T"
                                    }
                                }
                            ]
                        },
                        {
                            "name": "nyc-fw-secondary",
                            "device_redundancy_group_priority": 50,
                            "interfaces": [
                                {
                                    "type": "VIRTUAL",
                                    "name": "failover-link",
                                    "ip_addresses": [
                                        {
                                            "host": "172.27.48.1",
                                            "prefix_length": 31
                                        }
                                    ],
                                    "parent_interface": {
                                        "name": "gigabitethernet0/3",
                                        "type": "A_1000BASE_T"
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
        ]
    }
}
```

### Creating Cisco ASA Configuration Template - Common for Primary and Secondary Units

The following snippet represents an example Cisco ASA failover configuration template:

```python
# Configuration Template for Cisco ASA
template_body="""
{% set redundancy_members = gql_data['data']['devices'][0]['device_redundancy_group']['members'] %}
{% set failover_device_local = redundancy_members[0] if redundancy_members[0].name == device else redundancy_members[1] %}
{% set failover_device_peer = redundancy_members[0] if redundancy_members[0].name != device else redundancy_members[1] %}
{% set failover_local_vif = failover_device_local.interfaces | first %}
{% set failover_peer_vif = failover_device_peer.interfaces | first %}
!
hostname {{ device.name }}
!
failover lan unit {{ priority_mapping[failover_device_local.device_redundancy_group_priority] }}
failover lan interface {{ failover_local_vif.name }} {{ failover_local_vif.parent_interface.name }} 
!
failover interface ip {{ failover_local_vif.name }} {{ failover_local_vif.ip_addresses[0].host }}/{{ failover_local_vif.ip_addresses[0].prefix_length }} standby {{ failover_peer_vif.ip_addresses[0].host }}
interface {{ failover_local_vif.parent_interface.name }} 
  no shutdown
!
failover link {{ failover_local_vif.name }} {{ failover_local_vif.parent_interface.name }} 
!
!failover ipsec pre-shared-key !Nautobot Secrets
!
failover
!
"""
```

### Rendering Cisco ASA Configuration Template with the data retrieved from GraphQL

Following snippet represents an example Cisco ASA Failover rendered configuration:

```python
from jinja2 import Template

tm=Template(template_body)

nyc_fw_primary_config = tm.render(
    device=hostname,
    gql_data=gql_data,
    priority_mapping={50: 'secondary', 100: 'primary'}
)

print(nyc_fw_primary_config)
```

```text
!
hostname nyc-fw-primary
!
failover lan unit
failover lan interface failover-link gigabitethernet0/3
!
failover interface ip failover-link 172.27.48.0/31 standby 172.27.48.1
interface gigabitethernet0/3
  no shutdown
!
failover link failover-link gigabitethernet0/3
!
!failover ipsec pre-shared-key !Nautobot Secrets
!
failover
!
```

## Example use of Device Redundancy Groups - Spine Redundancy in a Leaf and Spine (Clos) Topology

Another example for the redundancy group use case could be a spine redundancy in the Leaf and Spine topology.
Spine redundancy is important while performing the Day-2 operations, such as OS-updates.

In this scenario, no more than 1 device participating in a Device Redundancy Group should be updated and rebooted at the same time. In order to track this, we will create a new Device custom field  named `upgrade_operational_state` and assign it one of the statues: `pre_upgrade`, `in_reboot`, `post_upgrade`. If a device with a spine role assigned is in state `in_reboot`, no other redundancy group members should be OS-upgraded at the same time.

### Querying for the data - Spine Redundancy in a Leaf and Spine (Clos) Topology

To retrieve the data about devices forming a Spine redundancy group, we will use the following GraphQL query:

```text
query {
    device_redundancy_groups(name__ie: "nyc-spines") {
        name
        members {
          name
          device_role {
            slug
          }
          cf_upgrade_operational_state
        }
    }
}
```

### Retrieving the data - Spine Redundancy in a Leaf and Spine (Clos) Topology

An example data returned from Nautobot is presented below.

```json
{
  "data": {
    "device_redundancy_groups": [
      {
        "name": "nyc-spines",
        "members": [
          {
            "name": "spine-1",
            "device_role": {
              "slug": "spine"
            },
            "cf_upgrade_operational_state": "in_reboot"
          },
          {
            "name": "spine-2",
            "device_role": {
              "slug": "spine"
            },
            "cf_upgrade_operational_state": null
          },
          {
            "name": "spine-3",
            "device_role": {
              "slug": "spine"
            },
            "cf_upgrade_operational_state": null
          },
          {
            "name": "spine-4",
            "device_role": {
              "slug": "spine"
            },
            "cf_upgrade_operational_state": null
          }
        ]
      }
    ]
  }
}
```

Based on the output, `spine-1` device is being rebooted at the moment of the GraphQL query response. This could be used by an automation system to prevent OS upgrades on `spine-2`, `spine-3`, `spine-4`.
