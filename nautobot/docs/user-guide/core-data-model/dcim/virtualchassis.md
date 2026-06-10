# Virtual Chassis

A virtual chassis represents a set of devices which share a common control plane. A common example of this is a stack of switches which are connected and configured to operate as a single device. A virtual chassis must be assigned a name and may be assigned a domain.

Each device in the virtual chassis is referred to as a VC member, and assigned a position and (optionally) a priority. VC member devices commonly reside within the same rack, though this is not a requirement. One of the devices may be designated as the VC master: This device will typically be assigned a name, services, and other attributes related to managing the VC.

You create your devices, then create the Virtual Chassis and assign the devices to the Virtual Chassis.

!!! note
    It's important to recognize the distinction between a virtual chassis and a chassis-based device. A virtual chassis is **not** suitable for modeling a chassis-based switch with removable line cards (such as the Juniper EX9208), as its line cards are _not_ physically autonomous devices. Chassis should be modeled with module bays and modules.

## Overview

The key piece of Virtual Chassis is when multiple physical devices operate as a **single logical device** with one management IP, such as a switch stack. The model itself is intentionally simple: a single `VirtualChassis` object that member devices point to, with each member recording its position in the stack. One member can be explicitly designated as the master, and Nautobot will surface all ports (interfaces, front ports, rear ports, etc.) from every member on that master device, reflecting how the stack actually presents itself on the network.

!!! note
    Interfaces are not "automatically" numbered. This is similar to the real world, in which when you get a device, the in interfaces presume a `1-slot`, such as `GigabitEthernet1/0/1`, but once you set it as the 3rd slot, the interface would be `GigabitEthernet1/0/1`. You are encouraged to use the Bulk Rename feature to bulk change the device interfaces.

LAG interfaces are supported across devices that have the same parent virtual chassis — this is the one case in Nautobot where a LAG's member interfaces may live on different devices. The LAG will show its member interfaces across the multiple devices on the LAG itself. The recommendation is to create the LAG interface itself (e.g. `PortChannel10`) on the expected master device. Because the chassis is a single logical device, the LAG fully captures the relationship on its own; no additional grouping model (such as an Interface Redundancy Group) is needed.

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Unique name identifying the virtual chassis |
| `master` | ForeignKey to Device | No | The device that acts as the control plane master for the chassis; all member devices are managed through this device |
| `domain` | string | No | Optional domain name shared across chassis members (used in some vendor implementations for identification) |

The following fields are on the `Device` model, in support of the Virtual Chassis featureset.

| Attribute | Type | Required | Description |
|---|---|---|---|
| `virtual_chassis` | ForeignKey to VirtualChassis | No | The virtual chassis this device belongs to |
| `vc_position` | integer (0–255) | Yes (if in VC) | Slot/position of this device within the virtual chassis; must be unique per chassis |
| `vc_priority` | integer (0–255) | No | Election priority for master role; higher values win (vendor behavior varies) |

## Entity Relationship Diagram

This schema illustrates the connections between the models involved in a virtual chassis.

TODO: Validate AI Generated ERD

```mermaid
---
title: Virtual Chassis Entity Relationship Diagram
---
erDiagram
    VirtualChassis {
        string name UK
        string domain
        Device master FK "one-to-one, optional"
    }

    Device {
        string name
        VirtualChassis virtual_chassis FK "optional"
        int vc_position "0-255, required if in a virtual chassis, unique per chassis"
        int vc_priority "0-255, optional master-election priority"
        DeviceType device_type FK
    }

    Interface {
        string name
        string type
        Device device FK
        Module module FK "optional, set when provided by an installed module"
        Interface lag FK "optional parent LAG"
    }

    ModuleBay {
        string name
        string position
        Device parent_device FK "exactly one of parent_device"
        Module parent_module FK "or parent_module is set"
    }

    Module {
        string serial
        ModuleType module_type FK
        ModuleBay parent_module_bay FK "one-to-one"
    }

    VirtualChassis |o--o{ Device : "members (virtual_chassis + vc_position)"
    VirtualChassis |o--o| Device : "master"
    Device ||--o{ Interface : "has"
    Device ||--o{ ModuleBay : "has"
    ModuleBay |o--o| Module : "installed_module"
    Module ||--o{ ModuleBay : "nested module bays"
    Module ||--o{ Interface : "module-provided interfaces"
    Interface }o--o| Interface : "LAG membership (lag)"
```

## Sample API - TODO:

## Sample Design Builder

The following [Design Builder](https://docs.nautobot.com/projects/design-builder/en/latest/) example models a two-member Cisco StackWise virtual chassis (`jcy-stackwise-01`). It demonstrates the patterns required to handle the circular dependency between a `Device` and its `VirtualChassis`: switch 1 is created first and tagged with `"!ref": "sw1"`, the `VirtualChassis` is then created inline with `master: "!ref:sw1"` and `deferred: true` so the master assignment happens after both objects exist, and the primary IPv4 address is similarly deferred until interface and IP assignments are in place. Switch 2 joins the existing chassis via `"!ref:virtual_chassis"`, and the stack ports between members are wired together using `"!connect_cable"` against the refs on switch 1.

```
devices:
    # Switch 1 of the stack
  - "!create_or_update:name": "jcy-stackwise-01"
    location__name: "JCY"
    status__name: "Active"
    device_type__model: "C9300-48P"
    role__name: "Access Switch"
    "!ref": "sw1"
    # Virtual chassis attributes
    vc_position: 1
    vc_priority: 15
    # Virtual chassis creation with deferred assignment (Device created first then VC created with switch 1 as master)
    virtual_chassis:
      "!create_or_update:name": "jcy-stackwise-01"
      domain: "jcy-stackwise-01"
      master: "!ref:sw1"
      deferred: true
      "!ref": "virtual_chassis"
    # Interfaces (subset for brevity)
    interfaces:
      - "!create_or_update:name": "GigabitEthernet0/0"
        type: "1000base-t"
        status__name: "Active"
        mgmt_only: true
        description: "Management Interface"
        ip_address_assignments:
          - "!create_or_update:ip_address__address": "192.168.1.10/24"
            ip_address:
              "!create_or_update:address": "192.168.1.10/24"
              "!create_or_update:parent": "192.168.1.0/24"
              status__name: "Active"
              "!ref": "sw1_mgmt_ip"
      - "!create_or_update:name": "StackPort1/1"
        type: "cisco-stackwise-480"
        status__name: "Active"
        "!ref": "sw1_stackport_1"
      - "!create_or_update:name": "StackPort1/2"
        type: "cisco-stackwise-480"
        status__name: "Active"
        "!ref": "sw1_stackport_2"
      - "!create_or_update:name": "Port-channel1"
        type: "lag"
        status__name: "Active"
        mode: "tagged"
        description: "Cross-stack uplink LAG to upstream distribution"
        "!ref": "po1"
      - "!create_or_update:name": "TenGigabitEthernet1/1/1"
        type: "10gbase-x-sfpp"
        status__name: "Active"
        description: "Uplink"
        lag: "!ref:po1"
    # Deferred IP assignment to avoid dependency issues with interface creation/assignment
    primary_ip4:
      "address": "!ref:sw1_mgmt_ip"
      deferred: true

    # Switch 2 of the stack
  - "!create_or_update:name": "jcy-stackwise-01:2"
    location__name: "JCY"
    status__name: "Active"
    device_type__model: "C9300-48P"
    role__name: "Access Switch"
    # VC assignment to existing VC with switch 1 as master
    virtual_chassis: "!ref:virtual_chassis"
    # VC attributes
    vc_position: 2
    vc_priority: 14
    # interfaces (subset for brevity)
    interfaces:
      - "!create_or_update:name": "GigabitEthernet0/0"
        type: "1000base-t"
        status__name: "Active"
        mgmt_only: true
        description: "Management"
        vrf: "!ref:mgmt_vrf"
      - "!create_or_update:name": "StackPort2/1"
        type: "cisco-stackwise-480"
        status__name: "Active"
        "!connect_cable":
          status__name: "Connected"
          to: "!ref:sw1_stackport_2"
      - "!create_or_update:name": "StackPort2/2"
        type: "cisco-stackwise-480"
        status__name: "Active"
        "!connect_cable":
          status__name: "Connected"
          to: "!ref:sw1_stackport_1"
      - "!create_or_update:name": "TenGigabitEthernet2/1/1"
        type: "10gbase-x-sfpp"
        status__name: "Active"
        description: "Uplink"
        lag: "!ref:po1"
    # No primary IP assignment on switch 2 to avoid conflicts with switch 1 management IP
```

## GraphQL

The following query retrieves a virtual chassis by name and uses the master device's `vc_interfaces` field to return every interface across all chassis members in a single flat list. `vc_interfaces` on the VC master expands to the master's own interfaces plus the non-management interfaces of every other member, so there is no need to walk `members -> interfaces` separately.

```graphql
query ($vc_name: [String]) {
  virtual_chassis(name: $vc_name) {
    name
    domain
    master {
      name
      vc_interfaces {
        name
        type
        enabled
        mac_address
        mode
        description
        device {
          name
          vc_position
        }
        lag {
          name
        }
        ip_addresses {
          address
        }
      }
    }
  }
}
```

Query variables:

```json
{
  "vc_name": "jcy-stackwise-01"
}
```

!!! note
    Because `vc_interfaces` is a property on the `Device` model, the same query can be run directly against the master device (e.g. `query { devices(name: ["jcy-stackwise-01"]) { vc_interfaces { ... } } }`) without going through `virtual_chassis` at all. Querying the `virtual_chassis` object is useful when you also need chassis-level attributes such as `domain` or want to confirm the master before traversing its interfaces.

## Key Charteristics

- Can you port channel across multiple devices? Yes — spanned EtherChannel is supported in FTD clustering
- Can you see all interfaces on the Primary (control node)? No — Each node can only see its interfaces, but all cluster interfaces are visible via FMC
- Can you see all interfaces on the Backup (data node)? No — only interfaces physically on that chassis module are visible locally
- On Primary, can you tell which interfaces are assigned to which device? No — Only the FMC can see all interfaces
- When do you see all the interfaces on the master device? You cannot - Only the FMC can see all interface
- Can you connect interfaces from master to non-master? Yes
- What should the naming standard be for the chassis device? Use the shared cluster name / FMC display name (logical single name)
- Should I use interface named templates? Yes

## Questions to ask of the data model

Given the data model, what questions would a user ask?

- Given a device, I would like to know whether it is a member of a virtual chassis.
- Given a device in a virtual chassis, I would like to know whether it is the master.
- Given a device in a virtual chassis, I would like to know its position (slot) within the stack.
- Given a device in a virtual chassis, I would like to know which member would be elected master next.
- Given a device in a virtual chassis, I would like to know its sibling members.
- Given a virtual chassis, I would like to know all of its member devices and how many there are.
- Given a virtual chassis, I would like to know how to connect to its management plane (the master's primary IP — the members do not have one of their own).
- Given a virtual chassis, I would like to know its domain or stack identifier.
- Given a virtual chassis, I would like to know every interface across all of its members.
- Given an interface shown on the master, I would like to know which physical member it actually lives on.
- Given a member device, I would like to know which stack/HA ports connect it to which sibling, and on which port (via cables).  TODO: Confirm
- Given a LAG, I would like to know its member interfaces and which stack member each one lives on.

## Dual-chassis Single Control Plane

Dual-chassis Single Control Plane VSS / StackWise Virtual (Cisco)

### Configuration Generation

_Standard Global Config_

```
!
switch virtual domain 200
  switch 1
!
```

> Note: Switch number is local, domain must match

_Management Plane_

```
int port-channel 201
 switchport
 switch virtual link 1
!
interface TenGigabitEthernet1/1/1
 description VSL Link
 no switchport
 no ip address
 no cdp enable
 channel-group 201 mode on
!
interface TenGigabitEthernet1/1/2
 description VSL Link
 no switchport
 no ip address
 no cdp enable
 channel-group 201 mode on
```

> Note: Port Channel is different on the different switches, e.g. 201 for switch 1 and 202 for switch 2

Switch 2:

_Standard Global Config_

```
switch virtual domain 200
  switch 2
```

_Management Plane_

> Note: Port Channel is different on the different switches, e.g. 201 for switch 1 and 202 for switch 2

```
interface port-channel 202
 switchport
 switch virtual link 1
!
interface TenGigabitEthernet2/1/1
 description VSL Link
 no switchport
 no ip address
 no cdp enable
 channel-group 202 mode on
!
interface TenGigabitEthernet2/1/2
 description VSL Link
 no switchport
 no ip address
 no cdp enable
 channel-group 202 mode on
```


_Data Plane_

Switch 1 & 2

```
interface port-channel2
  description VSL Link
  switchport mode trunk
  switchport trunk allowed vlan 10,20,30,40
!
interface TenGigabitEthernet1/0/1
  switchport mode trunk
  switchport trunk allowed vlan 10,20,30,40
  channel-group 2 mode active
!
interface TenGigabitEthernet2/0/1
  switchport mode trunk
  switchport trunk allowed vlan 10,20,30,40
  channel-group 2 mode active
```

> Note: this config is on a single management IP


## Multi-Chassis Stack
Multi-chassis Stack Stackwise / Virtual Chassis / Arista Stack / HPE IRF / Extreme SummitStack

### Configuration Generation

_Standard Global Config_

1. Master Switch (Primary)
Set a high priority (default is 1, max is 15) to ensure this switch wins the election.

```
switch 1 priority 15
switch 1 renumber 1
```

2. Member Switches (Non-Master)
Keep a lower priority. You should renumber them so their interfaces are easily identifiable (e.g., Member 2 uses 2/0/x).

```
switch 2 priority 1
switch 1 renumber 2
```

_Management Plane_

You only configure this once on the Master; it automatically propagates to all members.

- Option A: Using an SVI (VLAN interface)

```
interface Vlan1
 ip address 192.168.1.10 255.255.255.0
 no shut
```

- Option B: Using the Dedicated Management Port

```
interface Management0/0
 ip address 10.1.1.10 255.255.255.0
 no shut
```

_Data Plane_

Because the stack behaves as one logical switch, the configuration is identical to a standard Port-Channel, except the interface identifiers reflect the different stack members (e.g., 1/0/1 and 2/0/1).

```
interface Port-channel 1
 description Uplink-to-Core
 switchport mode trunk

interface GigabitEthernet 1/0/1 # <== 1 is member 1 of stack.
 channel-group 1 mode active

interface GigabitEthernet 2/0/1 # <== 2 is member 2 of stack.
 channel-group 1 mode active
```

### Firewall Cluster
Firewall Cluster Cisco FXOS / SRX


#### Configuration Generation

_FXOS Chassis — Physical Interface Config_

```
scope eth-uplink
  scope fabric a
    scope interface Ethernet1/1
      set port-type data
      enable
      exit
    scope interface Ethernet1/2
      set port-type data
      enable
      exit
    scope interface Ethernet1/3
      set port-type cluster
      enable
      exit
    scope interface Ethernet1/4
      set port-type cluster
      enable
      exit
    exit
  exit
```

> Note: Interfaces designated `cluster` type are reserved for CCL; `data` interfaces are assigned to logical devices

_FXOS Chassis — CCL Port Channel_

```
scope eth-uplink
  scope fabric a
    create port-channel 48
      set port-channel-mode active
      create member-port Ethernet1/3
      create member-port Ethernet1/4
      exit
    exit
  exit
```

> Note: The CCL port channel ID (48 in this example) must match on both chassis; use dedicated high-bandwidth interfaces

_FXOS Chassis — Logical Device (Cluster Bootstrap)_

```
scope ssa
  scope slot 1
    scope app-instance ftd FTD-CLUSTER
      set cluster-role control
      set cluster-group-id 1
      set ccl-network 192.0.2.0
      set ccl-mask 255.255.255.0
      exit
    exit
  exit
```

> Note: `cluster-role` is set to `control` on the primary chassis slot and `data` on all others; `cluster-group-id` must match across all members

