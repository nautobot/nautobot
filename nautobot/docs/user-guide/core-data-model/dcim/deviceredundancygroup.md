# Device Redundancy Groups

Device Redundancy Groups represent logical relationships between multiple devices. Typically, a redundancy group could represent a failover pair, failover group, or a load sharing cluster.
Device Redundancy Groups are created first, before the devices are assigned to the group.

A failover strategy represents intended operation mode of the group. Supported failover strategy are:

  - Active/Active
  - Active/Passive.

Secrets groups could be used to store secret information used by failover or a cluster of devices.

Device Redundancy Group Priority is a Device attribute defined during assigning a Device to a Device Redundancy Group. This field represents the priority the device has in the device redundancy group.

## Overview

TODO: Review all of these assertions in detail.

The key piece of Device Redundancy Groups is when multiple physical devices work together to provide high availability while each maintaining its **own control plane and management IP**, such as a firewall HA pair, a vPC/MLAG pair, or a load balancer cluster. The model itself is intentionally simple: a single `DeviceRedundancyGroup` object that member devices point to, with each member optionally recording a priority within the group to convey failover order (e.g. primary vs. secondary). The group itself carries the failover strategy (active/active or active/passive), a status, and optionally a Secrets Group for credentials shared across the members.

!!! note
    Unlike a Virtual Chassis, there is no master concept and interfaces are never surfaced on a peer device. Each member remains a fully independent device in Nautobot — with its own interfaces, inventory, configuration, and primary IP — reflecting that each unit is managed on its own. Which unit is "primary" is conveyed by `device_redundancy_group_priority`; the meaning of the value (whether higher or lower wins) follows vendor behavior, so be consistent across your groups.

LAG interfaces cannot span members of a Device Redundancy Group; a LAG and its member interfaces must belong to the same device (or the same virtual chassis). For multi-chassis technologies such as vPC or MLAG, the recommendation is to model a port channel on each member individually, then tie the pair together with an [Interface Redundancy Group](../core-data-model/dcim/interfaceredundancygroup.md): create one group per multi-chassis port channel, assign each member's LAG interface to it with a priority, and record the vPC/MLAG domain or pair ID in `protocol_group_id`. As users, we recommend giving the LAG the same name on both members (e.g. `Port-Channel10` on each switch) to match how the technology is typically configured, however this is not enforced nor is any configuratoins synced. The Interface Redundancy Group is the only thing in the data model relating them to each other.

An Interface Redundancy Group does not change or take over the interfaces themselves — each member's LAG remains an ordinary, independently configured interface on its own device. What the group models is the real-world relationship between them: the fact that two separately configured interfaces present a single logical entity to the rest of the network. Its protocol fields (HSRP, VRRP, GLBP, CARP), optional shared `virtual_ip`, and Secrets Group exist for the first hop redundancy protocol (FHRP) use case it was originally designed around, but the grouping itself applies to any set of redundant interfaces — pairing the per-member port channels of a vPC/MLAG domain is exactly that.

The device redundancy group model provides the following fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | String | Yes | Unique name identifying the redundancy group |
| `status` | Status | Yes | Lifecycle status of the group (e.g., Planned, Active, Decommissioning) |
| `description` | String | No | Brief human-readable description of the group's purpose |
| `failover_strategy` | Choice | No | How traffic is handled across members: `Active/Active` (both units process traffic simultaneously) or `Active/Passive` (one unit is standby until failover occurs) |
| `comments` | Text | No | Free-form notes about the group |
| `secrets_group` | FK → SecretsGroup | No | Credentials used to access devices in this group (e.g., shared enable password) |

The following fields are on the `Device` model, in support of the Virtual Chassis featureset.

| Field | Type | Required | Description |
|---|---|---|---|
| `device_redundancy_group` | FK → DeviceRedundancyGroup | No | The redundancy group this device belongs to |
| `device_redundancy_group_priority` | Integer (≥ 1) | No | Priority of this device within the group |


## Entity Relationship Diagram

This schema illustrates the connections between the models involved in a device redundancy group.

TODO: Validate AI Generated ERD

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

The below Python snippet is intended to work as you drop in to your iPython shell or file. It levergages the public demo. In addition, you can update the first set of variables to more easily integrate with other systems.

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

TODO: Validate this by running

```jinja2
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
          - "!create_or_update:ip_address__address": "192.168.1.20/24"
            ip_address:
              "!create_or_update:address": "192.168.1.20/24"
              "!create_or_update:parent": "192.168.1.0/24"
              status__name: "Active"
              "!ref": "rt01_mgmt_ip"
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
          - "!create_or_update:ip_address__address": "172.27.48.0/31"
            ip_address:
              "!create_or_update:address": "172.27.48.0/31"
              "!create_or_update:parent": "172.27.48.0/31"
              status__name: "Active"
    primary_ip4:
      "address": "!ref:rt01_mgmt_ip"
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
          - "!create_or_update:ip_address__address": "192.168.1.21/24"
            ip_address:
              "!create_or_update:address": "192.168.1.21/24"
              "!create_or_update:parent": "192.168.1.0/24"
              status__name: "Active"
              "!ref": "rt02_mgmt_ip"
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
          - "!create_or_update:ip_address__address": "172.27.48.1/31"
            ip_address:
              "!create_or_update:address": "172.27.48.1/31"
              "!create_or_update:parent": "172.27.48.0/31"
              status__name: "Active"
    primary_ip4:
      "address": "!ref:rt02_mgmt_ip"
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
- **When do you see all the interfaces on the master device?** You do not, each device always shows only its own interfaces
- **Can you connect interfaces from master to non-master?** The failover and stateful link interfaces connect the two units either directly or via a switch
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
- Given a multi-chassis port channel (vPC/MLAG), I would like to know the corresponding LAG on the peer device (via their shared interface redundancy group).  # TODO: confirm
- Given a controller, I would like to know whether it is deployed on a device redundancy group rather than a single device.

!!! tip
    You can answer all of these questions with the prior defined GraphQL query.

## Multi-chassis L2 Pair

Operating systems and technologies include VPC / MLAG (Cisco vPC, Arista MLAG, and Juniper MC-LAG variants).

### Configuration Generation

TODO: Validate these AI Generated configurations

The following example shows a Cisco NX-OS vPC pair (`nyc-nexus-01` and `nyc-nexus-02`) in vPC domain 10, with a vPC (Po10) down to an access switch.

Switch 1:

_Global / vPC Domain_

```
feature vpc
feature lacp
!
vpc domain 10
  role priority 10
  peer-keepalive destination 192.168.100.2 source 192.168.100.1 vrf management
  peer-switch
  peer-gateway
  auto-recovery
```

!!! note
    The vPC domain ID (10) must match on both peers — this is the value to record in `protocol_group_id` on the Interface Redundancy Group. The peer-keepalive runs between each switch's own management IP, reflecting the two independent control planes that make this a Device Redundancy Group rather than a Virtual Chassis.

_Peer-Link_

```
interface port-channel1
  description vPC Peer-Link to nyc-nexus-02
  switchport mode trunk
  switchport trunk allowed vlan 10,20,30,40
  spanning-tree port type network
  vpc peer-link
!
interface Ethernet1/53
  description vPC Peer-Link member
  switchport mode trunk
  channel-group 1 mode active
!
interface Ethernet1/54
  description vPC Peer-Link member
  switchport mode trunk
  channel-group 1 mode active
```

_vPC to Downstream Device_

```
interface port-channel10
  description vPC 10 to jcy-access-01
  switchport mode trunk
  switchport trunk allowed vlan 10,20
  vpc 10
!
interface Ethernet1/1
  description Member of Po10 (vPC 10)
  switchport mode trunk
  channel-group 10 mode active
```

Switch 2:

_Global / vPC Domain_

```
feature vpc
feature lacp
!
vpc domain 10
  role priority 20
  peer-keepalive destination 192.168.100.1 source 192.168.100.2 vrf management
  peer-switch
  peer-gateway
  auto-recovery
```

!!! note
    Only the role priority and the peer-keepalive source/destination differ from switch 1; the peer-link and downstream vPC configuration are identical on both peers.

_Peer-Link and vPC to Downstream Device_

```
interface port-channel1
  description vPC Peer-Link to nyc-nexus-01
  switchport mode trunk
  switchport trunk allowed vlan 10,20,30,40
  spanning-tree port type network
  vpc peer-link
!
interface Ethernet1/53
  description vPC Peer-Link member
  switchport mode trunk
  channel-group 1 mode active
!
interface Ethernet1/54
  description vPC Peer-Link member
  switchport mode trunk
  channel-group 1 mode active
!
interface port-channel10
  description vPC 10 to jcy-access-01
  switchport mode trunk
  switchport trunk allowed vlan 10,20
  vpc 10
!
interface Ethernet1/1
  description Member of Po10 (vPC 10)
  switchport mode trunk
  channel-group 10 mode active
```

!!! note
    The `vpc 10` number must match on both peers. The local port-channel ID is allowed to differ between peers, but keeping them identical (`Po10` ↔ `vpc 10` on both) is strongly recommended — this mirrors the data-model guidance above to give both members' LAG interfaces the same name and relate them with an Interface Redundancy Group.

_Downstream Device (jcy-access-01)_

```
interface Port-channel10
  description Uplink to nyc-nexus-01/nyc-nexus-02 (vPC 10)
  switchport mode trunk
  switchport trunk allowed vlan 10,20
!
interface GigabitEthernet1/0/1
  description Uplink to nyc-nexus-01 Eth1/1
  channel-group 10 mode active
!
interface GigabitEthernet1/0/2
  description Uplink to nyc-nexus-02 Eth1/1
  channel-group 10 mode active
```

!!! note
    From the downstream device's perspective, vPC is invisible — it is a standard LACP port channel whose member links happen to land on two different switches. In Nautobot the downstream side is modeled as an ordinary LAG on a single device; no special handling is required.

## Firewall HA pair

Operating systems and technologies include Palo Alto, Fortinet, and Cisco ASA

### Configuration Generation

_Primary (Active) Unit — Failover Config_

```
failover
failover lan unit primary
failover lan interface FAILOVER GigabitEthernet0/3
failover replication http
failover link STATEFUL GigabitEthernet0/4
failover interface ip FAILOVER 10.1.1.1 255.255.255.252 standby 10.1.1.2
failover interface ip STATEFUL 10.1.2.1 255.255.255.252 standby 10.1.2.2
```

_Interface Standby IPs (on Primary)_

```
interface GigabitEthernet0/0
 nameif outside
 security-level 0
 ip address 203.0.113.1 255.255.255.0 standby 203.0.113.2
!
interface GigabitEthernet0/1
 nameif inside
 security-level 100
 ip address 10.0.0.1 255.255.255.0 standby 10.0.0.2
```

!!! note
    Standby IP is assigned to the secondary unit's corresponding interface automatically

_Secondary (Standby) Unit — Failover Config_

```
failover
failover lan unit secondary
failover lan interface FAILOVER GigabitEthernet0/3
failover link STATEFUL GigabitEthernet0/4
failover interface ip FAILOVER 10.1.1.1 255.255.255.252 standby 10.1.1.2
failover interface ip STATEFUL 10.1.2.1 255.255.255.252 standby 10.1.2.2
```

!!! note
    The secondary unit receives the full running config from the primary after the failover link is established; interface IPs need not be set manually

## HA pairs

Operating systems and technologies include F5 BIG-IP, A10 Thunder, Viptela, Versa, and Silver Peak

### Configuration Generation

_Standard Global Config_

1. Device A (Primary)

    ```
    # Set the sync address (usually the internal or HA self-IP)
    modify cm device f5-01.local { configsync-ip 10.1.1.1 }
    # Add Device B to the trust (performed on Device A)
    run cm add-to-trust wire-address 10.1.1.2 user admin

    # Create the Group (On Primary):
    create cm device-group my_ha_group { devices { f5-01.local f5-02.local } type sync-failover }
    ```

2. Device B (Standby)

    ```
    # Set the sync address
    modify cm device f5-02.local { configsync-ip 10.1.1.2 }
    Create the Group (On Primary):
    ```

_Management Plane_

Each retains its own unique Management IP for individual access, but they share a Floating Self-IP for management traffic that needs to reach the "Active" unit (like SNMP or API calls).

**Device A (Primary)**

  ```
    modify sys global-settings mgmt-dhcp disabled
    create sys management-ip 192.168.1.10/24
    create net self floating_mgmt_ip { address 192.168.1.12/24 vlan internal floating enabled traffic-group traffic-group-1 }
  ```

**Device B (Standby)**

  ```
    create sys management-ip 192.168.1.11/24
    Floating Self-IP (Shared/Active):
  ```

_Data Plane_

Does not support Cross-Chassis EtherChannel. Instead, you build a "Trunk" on each device separately. Redundancy is handled by the Floating IP moving from Device A's Trunk to Device B's Trunk during a failover.

1. Create the Trunk (Do this on both units locally)

    ```
    create net trunk my_trunk { interfaces { 1.1 1.2 } lacp enabled }
    ```

2. Assign VLAN to the Trunk

    ```
    create net vlan internal_vlan { interfaces add { my_trunk { tagged } } }
    ```

3. Create the Floating IP (The "Gateway" for your servers)

    ```
    create net self internal_floating { address 10.10.1.1/24 vlan internal_vlan floating enabled traffic-group traffic-group-1 }
    ```
