# Device Redundancy Groups

Device Redundancy Groups represent logical relationships between multiple devices. Typically, a redundancy group could represent a failover pair, failover group, or a load sharing cluster.
Device Redundancy Groups are created first, before the devices are assigned to the group.

A failover strategy represents the intended operation mode of the group. Supported failover strategies are:

  - Active/Active
  - Active/Passive.

Secrets groups could be used to store secret information used by failover or a cluster of devices.

Device Redundancy Group Priority is a Device attribute set when assigning a Device to a Device Redundancy Group. This field represents the priority the device has in the device redundancy group.

## Overview

Choosing between this and a [Virtual Chassis](virtualchassis.md) comes down to the management control plane count — use a Device Redundancy Group when each member keeps its **own** control plane, and a Virtual Chassis when they share **one**. See [HA Devices](hadevice.md) for the full comparison.

Use a Device Redundancy Group when multiple physical devices work together to provide high availability while each keeps its **own control plane and management IP**, such as a firewall HA pair, a vPC/MLAG pair, or a load balancer cluster. The model is small: a single `DeviceRedundancyGroup` object that member devices point to, with each member optionally recording a priority within the group to convey failover order (e.g. primary vs. secondary). The group itself carries the failover strategy (active/active or active/passive), a status, and optionally a Secrets Group for credentials shared across the members.

!!! note
    Unlike a Virtual Chassis, there is no master concept and interfaces are never surfaced on a peer device. Each member remains a fully independent device in Nautobot — with its own interfaces, inventory, configuration, and primary IP — reflecting that each unit is managed on its own. Which unit is "primary" is conveyed by `device_redundancy_group_priority`, but Nautobot only stores this integer — it does not elect a primary or define whether higher or lower wins. Your automation assigns the meaning, so pick a convention and document it.

TODO: Review this as our final recommendation

LAG interfaces cannot span members of a Device Redundancy Group; a LAG and its member interfaces must belong to the same device (or the same virtual chassis). For multi-chassis technologies such as vPC or MLAG, the recommendation is to model a port channel on each member individually, then tie the pair together with an [Interface Redundancy Group](interfaceredundancygroup.md): create one group per multi-chassis port channel, assign each member's LAG interface to it with a priority, and record the vPC/MLAG domain or pair ID in `protocol_group_id` — the cross-vendor redundancy identifier (vPC domain, MLAG domain, cluster ID) that config templates read to render the domain/group lines. As users, we recommend giving the LAG the same name on both members (e.g. `Port-Channel10` on each switch) to match how the technology is typically configured; however, this is not enforced nor is any configuration synced. The Interface Redundancy Group is the only thing in the data model relating them to each other.

An Interface Redundancy Group does not change or take over the interfaces themselves — each member's LAG remains an ordinary, independently configured interface on its own device. What the group models is the relationship between them: two separately configured interfaces that present a single logical entity to the rest of the network. The `protocol` field is meant for first hop redundancy protocols (FHRP) such as VRRP, not for link aggregation protocols such as LACP; leave it blank when grouping port channels.

The device redundancy group model provides the following fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | String | Yes | Unique name identifying the redundancy group |
| `status` | Status | Yes | Lifecycle status of the group (e.g., Planned, Active, Decommissioning) |
| `description` | String | No | Brief human-readable description of the group's purpose |
| `failover_strategy` | Choice | No | How traffic is handled across members: `Active/Active` (both units process traffic simultaneously) or `Active/Passive` (one unit is standby until failover occurs) |
| `comments` | Text | No | Free-form notes about the group |
| `secrets_group` | FK → SecretsGroup | No | Credentials used to access devices in this group (e.g., shared enable password) |

The following fields are on the `Device` model, in support of the Device Redundancy Group feature set.

| Field | Type | Required | Description |
|---|---|---|---|
| `device_redundancy_group` | FK → DeviceRedundancyGroup | No | The redundancy group this device belongs to |
| `device_redundancy_group_priority` | Integer (≥ 1) | No | Priority of this device within the group |

## Entity Relationship Diagram

This schema illustrates the connections between the models involved in a device redundancy group.

```mermaid
---
title: Device Redundancy Group Entity Relationship Diagram
---
erDiagram
    DeviceRedundancyGroup {
        string name UK
        Status status FK
        string failover_strategy "active-active or active-passive, optional"
        SecretsGroup secrets_group FK "optional"
    }

    Device {
        string name
        DeviceRedundancyGroup device_redundancy_group FK "optional"
        int device_redundancy_group_priority "1+, optional, requires a group to be set"
        DeviceType device_type FK
    }

    Interface {
        string name
        string type
        Device device FK
        Interface lag FK "optional parent LAG"
    }

    Controller {
        string name UK
        Device controller_device FK "either controller_device"
        DeviceRedundancyGroup controller_device_redundancy_group FK "or this is set, not both"
    }

    InterfaceRedundancyGroup {
        string name UK
        Status status FK
        string protocol "HSRP, VRRP, GLBP, CARP, or blank for other groupings"
        string protocol_group_id "e.g. HSRP group ID or vPC domain ID"
        IPAddress virtual_ip FK "optional shared virtual address"
        SecretsGroup secrets_group FK "optional"
    }

    InterfaceRedundancyGroupAssociation {
        InterfaceRedundancyGroup interface_redundancy_group FK
        Interface interface FK
        int priority "required per member"
    }

    SecretsGroup {
        string name UK
    }

    DeviceRedundancyGroup |o--o{ Device : "members (device_redundancy_group + priority)"
    DeviceRedundancyGroup }o--o| SecretsGroup : "shared credentials"
    DeviceRedundancyGroup |o--o{ Controller : "controller deployed on group"
    Device ||--o{ Interface : "has (each member keeps its own)"
    Interface }o--o| Interface : "LAG membership (lag)"
    InterfaceRedundancyGroup ||--o{ InterfaceRedundancyGroupAssociation : "has"
    Interface ||--o{ InterfaceRedundancyGroupAssociation : "member (with priority)"
    InterfaceRedundancyGroup }o--o| SecretsGroup : "protocol secrets"
```

## Sample API

The below Python snippet is intended to work by dropping it into a iPython shell or file. It leverages the public demo sandbox. In addition, you can update the first set of variables to more easily integrate with other systems.

??? example "Show pynautobot script"

    ```python
    import sys
    import pynautobot

    NAUTOBOT_URL = "http://demo.nautobot.com"
    NAUTOBOT_TOKEN = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    ROLE_NAME = "router"
    ROOT_NAME = "jcy"
    MGMT_PREFIX = "192.168.1.0/24"
    FAILOVER_PREFIX = "172.27.48.0/31"
    DEVICE_TYPE_MODEL = "N9K-C9372TX"

    LOCATION_NAME = f"{ROOT_NAME.upper()}"
    DRG_NAME = f"{ROOT_NAME}-drg01:02"
    IRG_NAME = f"{ROOT_NAME}-drg-rt01:02-po10"
    SECRETS_GROUP_NAME = f"{ROOT_NAME}-drg-credentials"
    DEVICE_1_NAME = f"{ROOT_NAME}-drg-rt01"
    DEVICE_2_NAME = f"{ROOT_NAME}-drg-rt02"

    DEVICES = [
        {"name": DEVICE_1_NAME, "priority": 100, "mgmt_ip": "192.168.1.20/24", "failover_ip": "172.27.48.0/31"},
        {"name": DEVICE_2_NAME, "priority": 50, "mgmt_ip": "192.168.1.21/24", "failover_ip": "172.27.48.1/31"},
    ]

    nb = pynautobot.api(url=NAUTOBOT_URL, token=NAUTOBOT_TOKEN)


    def get_or_create(endpoint, lookup, defaults=None):
        """Return (record, created) for the given endpoint, matching pynautobot filter kwargs."""
        record = endpoint.get(**lookup)
        if record:
            return record, False
        return endpoint.create(**{**lookup, **(defaults or {})}), True


    def log(created, kind, name):
        print(f"  {'created' if created else 'exists '}  {kind}: {name}")


    active = nb.extras.statuses.get(name="Active")
    location = nb.dcim.locations.get(name=LOCATION_NAME)
    device_type = nb.dcim.device_types.get(model=DEVICE_TYPE_MODEL)
    namespace = nb.ipam.namespaces.get(name="Global")
    for obj, label in [
        (active, "Status Active"),
        (location, f"Location {LOCATION_NAME}"),
        (device_type, f"DeviceType {DEVICE_TYPE_MODEL}"),
        (namespace, "Namespace Global"),
    ]:
        if obj is None:
            sys.exit(f"Prerequisite not found in {NAUTOBOT_URL}: {label}")

    print("Seeding prerequisites...")
    role = nb.extras.roles.get(name=ROLE_NAME)

    for prefix in (MGMT_PREFIX, FAILOVER_PREFIX):
        _, created = get_or_create(
            nb.ipam.prefixes, {"prefix": prefix, "namespace": namespace.id}, {"status": active.id}
        )
        log(created, "Prefix", prefix)

    secrets_group, created = get_or_create(nb.extras.secrets_groups, {"name": SECRETS_GROUP_NAME})
    log(created, "SecretsGroup", secrets_group.name)

    print("Seeding device redundancy group...")
    drg, created = get_or_create(
        nb.dcim.device_redundancy_groups,
        {"name": DRG_NAME},
        {"status": active.id, "failover_strategy": "active-active", "secrets_group": secrets_group.id},
    )
    log(created, "DeviceRedundancyGroup", drg.name)

    lag_ids = {}
    for spec in DEVICES:
        print(f"Seeding {spec['name']}...")
        device, created = get_or_create(
            nb.dcim.devices,
            {"name": spec["name"]},
            {
                "device_type": device_type.id,
                "role": role.id,
                "location": location.id,
                "status": active.id,
                "device_redundancy_group": drg.id,
                "device_redundancy_group_priority": spec["priority"],
            },
        )
        log(created, "Device", device.name)

        mgmt, created = get_or_create(
            nb.dcim.interfaces,
            {"device": device.id, "name": "Management0"},
            {"type": "1000base-t", "status": active.id, "mgmt_only": True, "description": "Management Interface"},
        )
        log(created, "Interface", f"{device.name} Management0")

        mgmt_ip, created = get_or_create(
            nb.ipam.ip_addresses, {"address": spec["mgmt_ip"], "namespace": namespace.id}, {"status": active.id}
        )
        log(created, "IPAddress", str(mgmt_ip.address))
        _, created = get_or_create(nb.ipam.ip_address_to_interface, {"interface": mgmt.id, "ip_address": mgmt_ip.id})
        log(created, "IP assignment", f"{mgmt_ip.address} -> {device.name} Management0")
        device.update({"primary_ip4": mgmt_ip.id})

        failover_parent, created = get_or_create(
            nb.dcim.interfaces,
            {"device": device.id, "name": "GigabitEthernet0/3"},
            {"type": "1000base-t", "status": active.id, "description": "Failover physical parent"},
        )
        log(created, "Interface", f"{device.name} GigabitEthernet0/3")

        failover_link, created = get_or_create(
            nb.dcim.interfaces,
            {"device": device.id, "name": "failover-link"},
            {
                "type": "virtual",
                "status": active.id,
                "parent_interface": failover_parent.id,
                "description": "HA failover link",
            },
        )
        log(created, "Interface", f"{device.name} failover-link")

        failover_ip, created = get_or_create(
            nb.ipam.ip_addresses, {"address": spec["failover_ip"], "namespace": namespace.id}, {"status": active.id}
        )
        log(created, "IPAddress", str(failover_ip.address))
        _, created = get_or_create(
            nb.ipam.ip_address_to_interface, {"interface": failover_link.id, "ip_address": failover_ip.id}
        )
        log(created, "IP assignment", f"{failover_ip.address} -> {device.name} failover-link")

        po10, created = get_or_create(
            nb.dcim.interfaces,
            {"device": device.id, "name": "Port-Channel10"},
            {"type": "lag", "status": active.id, "description": "Multi-chassis port channel (vPC 10)"},
        )
        log(created, "Interface", f"{device.name} Port-Channel10")
        lag_ids[device.name] = po10.id

        for member_name in ("Ethernet1/1", "Ethernet1/2"):
            member, created = get_or_create(
                nb.dcim.interfaces,
                {"device": device.id, "name": member_name},
                {"type": "10gbase-x-sfpp", "status": active.id, "lag": po10.id, "description": "Member of Po10"},
            )
            log(created, "Interface", f"{device.name} {member_name}")
            if member.lag is None:
                member.update({"lag": po10.id})

    print("Seeding interface redundancy group...")
    irg, created = get_or_create(
        nb.dcim.interface_redundancy_groups,
        {"name": IRG_NAME},
        {"status": active.id, "protocol": "vrrp", "protocol_group_id": "10"},
    )
    log(created, "InterfaceRedundancyGroup", irg.name)

    for spec in DEVICES:
        _, created = get_or_create(
            nb.dcim.interface_redundancy_group_associations,
            {"interface_redundancy_group": irg.id, "interface": lag_ids[spec["name"]]},
            {"priority": spec["priority"]},
        )
        log(created, "IRG association", f"{spec['name']} Port-Channel10 (priority {spec['priority']})")

    ```

## Sample Design Builder

The following [Design Builder](https://docs.nautobot.com/projects/design-builder/en/latest/) example models the same HA pair as the Sample API above: `jcy-drg-rt01` and `jcy-drg-rt02` tied together by a `DeviceRedundancyGroup` named `jcy-drg01:02`, sharing the same `JCY` location and `192.168.1.0/24` management prefix.

??? example "Show Design Builder YAML"

    ```jinja2
    # Prefixes are created first so the IPs below can parent to them.
    prefixes:
      - "!create_or_update:prefix": "192.168.1.0/24"
        status__name: "Active"
        "!ref": "mgmt_prefix"
      - "!create_or_update:prefix": "172.27.48.0/31"
        status__name: "Active"
        "!ref": "failover_prefix"

    device_redundancy_groups:
      - "!create_or_update:name": "jcy-drg01:02"
        status__name: "Active"
        failover_strategy: "active-active"
        description: "HA pair for JCY"
        "!ref": "jcy_drg"

    devices:
        # Primary unit
      - "!create_or_update:name": "jcy-drg-rt01"
        location__name: "JCY"
        status__name: "Active"
        device_type__model: "C9300"
        role__name: "router"
        device_redundancy_group: "!ref:jcy_drg"
        device_redundancy_group_priority: 100
        interfaces:
          - "!create_or_update:name": "Management0"
            type: "1000base-t"
            status__name: "Active"
            mgmt_only: true
            description: "Management Interface"
            ip_address_assignments:
              - ip_address:
                  "!create_or_update:address": "192.168.1.20/24"
                  "!create_or_update:parent": "!ref:mgmt_prefix"
                  status__name: "Active"
          - "!create_or_update:name": "GigabitEthernet0/3"
            type: "1000base-t"
            status__name: "Active"
            description: "Failover physical parent"
            "!ref": "rt01_failover_parent"
          - "!create_or_update:name": "failover-link"
            type: "virtual"
            status__name: "Active"
            parent_interface: "!ref:rt01_failover_parent"
            description: "HA failover link"
            ip_address_assignments:
              - ip_address:
                  "!create_or_update:address": "172.27.48.0/31"
                  "!create_or_update:parent": "!ref:failover_prefix"
                  status__name: "Active"
        # `!get` looks the address up after the interface and its IP exist; `deferred`
        # waits until the device is saved before assigning it.
        primary_ip4:
          "!get:address": "192.168.1.20/24"
          deferred: true

        # Secondary unit
      - "!create_or_update:name": "jcy-drg-rt02"
        location__name: "JCY"
        status__name: "Active"
        device_type__model: "C9300"
        role__name: "router"
        device_redundancy_group: "!ref:jcy_drg"
        device_redundancy_group_priority: 50
        interfaces:
          - "!create_or_update:name": "Management0"
            type: "1000base-t"
            status__name: "Active"
            mgmt_only: true
            description: "Management Interface"
            ip_address_assignments:
              - ip_address:
                  "!create_or_update:address": "192.168.1.21/24"
                  "!create_or_update:parent": "!ref:mgmt_prefix"
                  status__name: "Active"
          - "!create_or_update:name": "GigabitEthernet0/3"
            type: "1000base-t"
            status__name: "Active"
            description: "Failover physical parent"
            "!ref": "rt02_failover_parent"
          - "!create_or_update:name": "failover-link"
            type: "virtual"
            status__name: "Active"
            parent_interface: "!ref:rt02_failover_parent"
            description: "HA failover link"
            ip_address_assignments:
              - ip_address:
                  "!create_or_update:address": "172.27.48.1/31"
                  "!create_or_update:parent": "!ref:failover_prefix"
                  status__name: "Active"
        # `!get` looks the address up after the interface and its IP exist; `deferred`
        # waits until the device is saved before assigning it.
        primary_ip4:
          "!get:address": "192.168.1.21/24"
          deferred: true
    ```

## GraphQL

The following query retrieves a device redundancy group by name, without needing to know any of the member hostnames up front. It is built to answer the "Questions to ask of the data model" below in a single call.

!!! note
    The `failover_links: interfaces(name__ie: "failover-link")` is a convention, this would work in a scenario where you defined your interface to be named `failover-link`. You can choose other methods (such as a tag or role) and would need ot update accordingly.

```graphql
query ($redundancy_group: [String]) {
  device_redundancy_groups(name: $redundancy_group) {
    name
    failover_strategy
    secrets_group {
      name
    }
    controllers {
      name
    }
    devices {
      name
      device_redundancy_group_priority
      primary_ip4 {
        address
      }
      lag_interfaces: interfaces (interface_redundancy_groups__isnull: false, lag__isnull: true) {
        name
        interface_redundancy_groups {
          name
          protocol_group_id
        }
        member_interfaces {
          name
        }
      }
      failover_links: interfaces(name__ie: "failover-link") {
        type
        name
        ip_addresses {
          host
          mask_length
        }
      }
    }
  }
}
```

Query variables:

```json
{
  "redundancy_group": "jcy-drg01:02"
}
```

An example of the data returned from Nautobot is presented below.

```json
{
  "data": {
    "device_redundancy_groups": [
      {
        "name": "jcy-drg01:02",
        "failover_strategy": "ACTIVE_ACTIVE",
        "secrets_group": {
          "name": "jcy-drg-credentials"
        },
        "controllers": [],
        "devices": [
          {
            "name": "jcy-drg-rt01",
            "device_redundancy_group_priority": 100,
            "primary_ip4": {
              "address": "192.168.1.20/24"
            },
            "lag_interfaces": [
              {
                "name": "Port-Channel10",
                "interface_redundancy_groups": [
                  {
                    "name": "jcy-drg-rt01:02-po10",
                    "protocol_group_id": "10"
                  }
                ],
                "member_interfaces": [
                  {
                    "name": "Ethernet1/1"
                  },
                  {
                    "name": "Ethernet1/2"
                  }
                ]
              }
            ],
            "failover_links": [
              {
                "type": "VIRTUAL",
                "name": "failover-link",
                "ip_addresses": [
                  {
                    "host": "172.27.48.0",
                    "mask_length": 31
                  }
                ]
              }
            ]
          },
          {
            "name": "jcy-drg-rt02",
            "device_redundancy_group_priority": 50,
            "primary_ip4": {
              "address": "192.168.1.21/24"
            },
            "lag_interfaces": [
              {
                "name": "Port-Channel10",
                "interface_redundancy_groups": [
                  {
                    "name": "jcy-drg-rt01:02-po10",
                    "protocol_group_id": "10"
                  }
                ],
                "member_interfaces": [
                  {
                    "name": "Ethernet1/1"
                  },
                  {
                    "name": "Ethernet1/2"
                  }
                ]
              }
            ],
            "failover_links": [
              {
                "type": "VIRTUAL",
                "name": "failover-link",
                "ip_addresses": [
                  {
                    "host": "172.27.48.1",
                    "mask_length": 31
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

!!! note
    The same data is reachable starting from a member device (e.g. `query { devices(name: ["nyc-fw-primary"]) { device_redundancy_group { devices { ... } } } }`) when a hostname is what you have in hand.

## Key Characteristics

- **Can you port channel across multiple devices?** No, but you can use interface redundancy groups to provide relationships between port channel virtual interfaces on two devices.
- **Can you see all interfaces on the Primary?** No — the active unit only shows its own interfaces
- **Can you see all interfaces on the Backup?** No — the standby unit has its own separate interface list
- **On Primary, can you tell which interfaces are assigned to which device?** N/A — each device is modeled separately in Nautobot
- **When do you see all the interfaces on the primary device?** You do not, each device always shows only its own interfaces
- **Can you connect interfaces from primary to non-primary?** The failover and stateful link interfaces connect the two units either directly or via a switch
- **What should the naming standard be for the HA pair?** A combination of the two devices names (e.g., `ASA01:02` for `ASA01` and `ASA02`)
- **Should I use interface named templates?** Yes

## Questions to ask of the data model

Given the data model, what questions would a user ask?

- Given a device, I would like to know whether it is part of a redundant deployment (a device redundancy group).
- Given a device in a redundancy group, I would like to know whether it is the primary (per its priority).
- Given a device in a redundancy group, I would like to know which member is next in line to take over.
- Given a device in a redundancy group, I would like to know its sibling members.
- Given a redundancy group, I would like to know all of its member devices and how many there are.
- Given a member device, I would like to know how to connect to its management plane (each member keeps its own primary IP).
- Given a redundancy group, I would like to know whether failover is active/active or active/passive.
- Given a redundancy group, I would like to know which credentials (Secrets Group) to use to access its members.
- Given a member device, I would like to know which interfaces form the HA/failover/peer link, and which port on the peer they connect to (via cables).
- Given a multi-chassis port channel (vPC/MLAG), I would like to know the corresponding LAG on the peer device (via their shared interface redundancy group).
- Given a controller, I would like to know whether it is deployed on a device redundancy group rather than a single device.

!!! tip
    You can answer all of these questions with the prior defined GraphQL query.

## Configuration Generation

=== "Multi-chassis L2 Pair"

    Operating systems and technologies include VPC / MLAG (Cisco vPC, Arista MLAG, and Juniper MC-LAG variants).

    A config template driven by the GraphQL response above. Each device renders its vPC domain (from the Interface Redundancy Group `protocol_group_id`), a peer-keepalive between the two members' management IPs, and each vPC port channel with its member interfaces.

    ```jinja2
    {% set group = data.device_redundancy_groups[0] %}
    {% for device in group.devices %}
    {% set peer = group.devices | rejectattr("name", "equalto", device.name) | first %}
    {% set group_id = device.lag_interfaces[0].interface_redundancy_groups[0].protocol_group_id %}
    # ~~~~~ {{ device.name }} ~~~~~

    # Global / vPC Domain

    feature vpc
    feature lacp
    !
    vpc domain {{ group_id }}
      role priority {{ device.device_redundancy_group_priority }}
      peer-keepalive destination {{ peer.primary_ip4.address.split("/")[0] }} source {{ device.primary_ip4.address.split("/")[0] }} vrf management
      peer-switch
      peer-gateway
      auto-recovery

    # note: vPC domain ID / `protocol_group_id` ({{ group_id }}) must match on both peers

    # Peer-Link Configuration

    interface port-channel1
      description vPC Peer-Link to {{ peer.name }}
      switchport mode trunk
      spanning-tree port type network
      vpc peer-link

    # vPC to Downstream Device Configuration
    {% for lag in device.lag_interfaces %}
    interface {{ lag.name }}
      description vPC {{ group_id }} downstream
      switchport mode trunk
      vpc {{ group_id }}
    !
    {% for member in lag.member_interfaces %}
    interface {{ member.name }}
      description Member of {{ lag.name }} (vPC {{ group_id }})
      switchport mode trunk
      channel-group {{ lag.name | replace("Port-Channel", "") }} mode active
    !
    {% endfor %}
    {% endfor %}
    {% endfor %}
    ```

    !!! note
        From the downstream device's perspective, vPC is a standard LACP port channel even though the interface are on two different switches. In Nautobot the downstream side is modeled as an ordinary LAG on a single device; no special handling is required.

=== "Firewall HA pair"

    Operating systems and technologies include Palo Alto, Fortinet, and Cisco ASA

    ```jinja2
    {% set group = data.device_redundancy_groups[0] %}
    {% set ordered = group.devices | sort(attribute="device_redundancy_group_priority", reverse=true) %}
    {% set primary = ordered | first %}
    {% for device in ordered %}
    {% set peer = group.devices | rejectattr("name", "equalto", device.name) | first %}
    # ~~~~~ {{ device.name }} ({{ "Primary/Active" if device.name == primary.name else "Secondary/Standby" }}) ~~~~~

    ## Failover Config

    failover
    failover lan unit {{ "primary" if device.name == primary.name else "secondary" }}
    {% for link in device.failover_links %}
    failover lan interface FAILOVER {{ link.name }}
    failover interface ip FAILOVER {{ link.ip_addresses[0].host }} {{ link.ip_addresses[0].mask_length | netmask }} standby {{ peer.failover_links[0].ip_addresses[0].host }}
    {% endfor %}
    {% endfor %}
    ```

    !!! note
        The secondary unit receives the full running config from the primary after the failover link is established; interface IPs need not be set manually

=== "HA pairs"

Operating systems and technologies include F5 BIG-IP, A10 Thunder, Viptela, Versa, and Silver Peak.

!!! note
    For the templating below this was added to the GraphQL query for simplicity.
    ```
      interfaces {
        name
        ip_addresses {
          float: parent {
            network
            prefix_length
          }
          address
        }
      }
      ```

### Configuration Generation

??? data "GraphQL data returned"

```json
{
  "data": {
    "device_redundancy_groups": [
      {
        "name": "ANY01-bigip-drg",
        "failover_strategy": "ACTIVE_PASSIVE",
        "secrets_group": null,
        "controllers": [],
        "devices": [
          {
            "name": "bigip1",
            "device_redundancy_group_priority": 1,
            "primary_ip4": {
              "address": "192.0.2.10/24"
            },
            "interfaces": [
              {
                "name": "HA",
                "ip_addresses": [
                  {
                    "float": {
                      "network": "198.51.100.0",
                      "prefix_length": 24
                    },
                    "address": "198.51.100.10/24"
                  }
                ]
              },
              {
                "name": "MGMT",
                "ip_addresses": [
                  {
                    "float": {
                      "network": "192.0.2.0",
                      "prefix_length": 24
                    },
                    "address": "192.0.2.10/24"
                  }
                ]
              },
              {
                "name": "external",
                "ip_addresses": [
                  {
                    "float": {
                      "network": "203.0.113.0",
                      "prefix_length": 25
                    },
                    "address": "203.0.113.10/25"
                  }
                ]
              },
              {
                "name": "internal",
                "ip_addresses": [
                  {
                    "float": {
                      "network": "203.0.113.128",
                      "prefix_length": 25
                    },
                    "address": "203.0.113.140/25"
                  }
                ]
              }
            ]
          },
          {
            "name": "bigip2",
            "device_redundancy_group_priority": 2,
            "primary_ip4": {
              "address": "192.0.2.11/24"
            },
            "interfaces": [
              {
                "name": "HA",
                "ip_addresses": [
                  {
                    "float": {
                      "network": "198.51.100.0",
                      "prefix_length": 24
                    },
                    "address": "198.51.100.11/24"
                  }
                ]
              },
              {
                "name": "MGMT",
                "ip_addresses": [
                  {
                    "float": {
                      "network": "192.0.2.0",
                      "prefix_length": 24
                    },
                    "address": "192.0.2.11/24"
                  }
                ]
              },
              {
                "name": "external",
                "ip_addresses": [
                  {
                    "float": {
                      "network": "203.0.113.0",
                      "prefix_length": 25
                    },
                    "address": "203.0.113.11/25"
                  }
                ]
              },
              {
                "name": "internal",
                "ip_addresses": [
                  {
                    "float": {
                      "network": "203.0.113.128",
                      "prefix_length": 25
                    },
                    "address": "203.0.113.141/25"
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

The template to generate both F5 configurations for Active and Passive.

```j2
{% set group = data.device_redundancy_groups[0] %}
{% for device in group.devices %}
{% set peer = group.devices | rejectattr("name", "equalto", device.name) | first %}

modify sys global-settings hostname {{ device.name }}{{ device}}
mv cm device bigip1 {{ device.name }}

{% for interface in device.interfaces %}
{% if "external" in interface.name %}
create net vlan {{ interface.name }} interfaces add { 1.1 }
create net self {{ interface.name }}-self address {{ interface.ip_addresses[0].address }} vlan {{ interface.name }}

{% elif "HA" in interface.name %}
create net vlan {{ interface.name }} interfaces add { 1.2 }
create net self {{ interface.name }}-self address {{ interface.ip_addresses[0].address }} vlan {{ interface.name }}
modify cm device {{ device.name }} configsync-ip {{ interface.ip_addresses[0].address.split("/")[0] }}
modify cm device {{ device.name }} unicast-address { { ip {{ interface.ip_addresses[0].address.split("/")[0] }} } { ip {{ device.primary_ip4.address.split("/")[0] }} } }
modify cm device {{ device.name }} mirror-ip {{ interface.ip_addresses[0].address.split("/")[0] }}
{% elif "internal" in interface.name %}
create net vlan {{ interface.name }} interfaces add { 1.3 }
create net self {{ interface.name }}-self address {{ interface.ip_addresses[0].address }} vlan {{ interface.name }}
{% endif %}
{% endfor %}


{% if device.device_redundancy_group_priority == 1 %}
modify cm trust-domain Root ca-devices add { {{ peer.primary_ip4.address.split("/")[0] }} } name {{ peer.name }} username admin password <peer-admin-password>
create cm device-group HA-group devices add { {{ device.name }} {{ peer.name }} } type sync-failover auto-sync enabled network-failover enabled
run cm config-sync to-group HA-group

{% for interface in device.interfaces %}
{% if "external" in interface.name %}
create net self {{ interface.name }}-float address {{ interface.ip_addresses[0]["float"]["network"].split(".")[:3] | join(".") }}.20/{{ interface.ip_addresses[0]["float"]["prefix_length"] }} vlan {{ interface.name }} traffic-group traffic-group-1
{% elif "internal" in interface.name %}
create net self {{ interface.name }}-float address {{ interface.ip_addresses[0]["float"]["network"].split(".")[:3] | join(".") }}.150/{{ interface.ip_addresses[0]["float"]["prefix_length"] }} vlan {{ interface.name }} traffic-group traffic-group-1
{% endif %}
{% endfor %}
{% endif %}
{% endfor %}
```

_Full Configuration for HA Pair_


1. Device A (Primary)

    ```
    # Set hostname.
    modify sys global-settings hostname bigip1
    mv cm device bigip1 bigip1

    # Create the HA VLAN + self IP — the dedicated link used for sync and heartbeats.
    create net vlan HA interfaces add { 1.2 }
    create net self HA-self address 198.51.100.10/24 vlan HA
    create net vlan external interfaces add { 1.1 }
    create net self external-self address 203.0.113.10/25 vlan external
    create net vlan internal interfaces add { 1.3 }
    create net self internal-self address 203.0.113.140/25 vlan internal

    # Set the ConfigSync address — where config is pushed/pulled.
    modify cm device bigip1 configsync-ip 198.51.100.10

    # Set failover (unicast) addresses — heartbeat over the HA link, with mgmt as backup path.
    modify cm device bigip1 unicast-address { { ip 198.51.100.10 } { ip 192.0.2.10 } }

    # Set the mirroring address — for connection mirroring (optional but recommended).
    modify cm device bigip1 mirror-ip 198.51.100.10

    # Establish device trust (one device only) — point at the peer's management IP and admin creds.
    modify cm trust-domain Root ca-devices add { 192.0.2.11 } name bigip2 username admin password <peer-admin-password>

    # Create the sync-failover device group (one device only) — this is the HA pair itself.
    create cm device-group HA-group devices add { bigip1 bigip2 } type sync-failover auto-sync enabled network-failover enabled
    run cm config-sync to-group HA-group

    # Create the floating self IP (one device only) — lives in traffic-group-1, moves to whichever unit is active.
    create net self external-float address 203.0.113.20/25 vlan external traffic-group traffic-group-1
    create net self internal-float address 203.0.113.20/25 vlan internal traffic-group traffic-group-1
    ```

2. Device B (Standby)

    ```
    # Set hostname.
    modify sys global-settings hostname bigip2
    mv cm device bigip1 bigip2

    # Create the HA VLAN + self IP — the dedicated link used for sync and heartbeats.
    create net vlan HA interfaces add { 1.2 }
    create net self HA-self address 198.51.100.11/24 vlan HA
    create net vlan external interfaces add { 1.1 }
    create net self external-self address 203.0.113.11/25 vlan external
    create net vlan internal interfaces add { 1.3 }
    create net self internal-self address 203.0.113.141/25 vlan internal

    # Set the ConfigSync address — where config is pushed/pulled.
    modify cm device bigip2 configsync-ip 198.51.100.10

    # Set failover (unicast) addresses — heartbeat over the HA link, with mgmt as backup path.
    modify cm device bigip2 unicast-address { { ip 198.51.100.10 } { ip 192.0.2.11 } }

    # Set the mirroring address — for connection mirroring (optional but recommended).
    modify cm device bigip2 mirror-ip 198.51.100.10


## Generating the Configuration

The script below renders the templates against GraphQL query. Paste the GraphQL query from the [GraphQL](#graphql) section into a variable called `GRAPHQL_QUERY`, and one of the three templates above into `CLI_CONFIG_TEMPLATE`. This script is a continuation of the prior script above and assumes the variables `nb`, `NAUTOBOT_URL`, and `NAUTOBOT_TOKEN` are already set.

??? example "Config Generation Script"

    ```python
    GRAPHQL_QUERY = """."""              # Replace with the GraphQL query from above
    CLI_CONFIG_TEMPLATE = """."""         # Replace with one of the three config templates above

    import ipaddress

    from jinja2 import Environment

    REDUNDANCY_GROUP = "jcy-drg01:02"


    def netmask(prefix_length):
        """Render a prefix length (e.g. 31) as a dotted netmask (255.255.255.254)."""
        return str(ipaddress.ip_network(f"0.0.0.0/{prefix_length}").netmask)


    gql = nb.graphql.query(query=GRAPHQL_QUERY, variables={"redundancy_group": REDUNDANCY_GROUP})

    env = Environment(trim_blocks=True, lstrip_blocks=True)
    env.filters["netmask"] = netmask

    print(env.from_string(CLI_CONFIG_TEMPLATE).render(**gql.json))
