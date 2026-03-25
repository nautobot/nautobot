# Redundant Devices 

Infrastructure is typically designed with redundancy in mind, prompting vendors to develop various technologies to support different high availability (HA) strategies. These include a range of protocols, connection types, synchronization systems, and terminology.

This creates a complex ecosystem that can be challenging to navigate, especially when determining how to model redundant infrastructure in Nautobot or which model to select. This guide aims to provide a clear and comprehensive approach to documenting redundant device infrastructure by covering:

- Use Cases
- Vendor Implementations
- Data Model Overview
- GraphQL Queries
- Key questions for the data model
- Configuration stanzas
- API Calls using pynautobot snippets
- Design Builder snippets

## Use Cases

The primary use cases to consider when creating, updating, or documenting redundant device models are:

- **Inventory Management:** Tracking assets and device details.
- **Configuration Management:** Generating and managing device configurations.
- **HA Resiliency:** Understanding and documenting network fault tolerance.

To help guide these use cases, we will ask and answer each of these questions to go with the best practices:

- Can you port channel across multiple devices?
- Can you see all interfaces on the Primary? 
- Can you see all interfaces on the Backup? 
- On Primary, can you tell which interfaces are assigned to which device? 
- When do you see all the interfaces on the master device?
- Can you connect interfaces from master to non-master? 
- Any configurations don't map back to model? 
- How are interfaces named?
- What should the naming standard be for the chassis device?
- Should I use interface named templates?

## Vendor Implementations

While vendors offer a variety of technologies, the data model remains largely agnostic to these specifics. The following table serves as a foundation for modeling redundant devices in Nautobot.

|     | Dual-chassis Single Control Plane | Multi-chassis Stack | Firewall Cluster | Multi-chassis L2 Pair | Firewall HA Pair | HA Pairs |
| --- | --- | --- | --- | --- | --- | --- |
| Example Technologies | VSS / StackWise Virtual / SRX | StackWise / VC / Arista Stack / IRF / SummitStack | Cisco FXOS | vPC / MLAG | PAN / Fortinet / ASA | LB / F5 / A10 / Viptela / Versa / Silver Peak |
| Management Control Plane Count | 1* | 1 | 1 | 2 | 2 | 2 |
| Physical Device Count | 2 | 2+ | 2+ | 2+ | 2 | 2 |
| Prompt Identity<br>(CLI Hostname) | Shared<br>(single logical hostname) | Shared<br>(single logical hostname) | Shared<br>(single logical hostname) | Per-device | Per-device<br>(may show active or similar) | Per-device<br>(may show active or similar) |
| Sibling Awareness | Yes (members) | Yes (members) | Yes (members) | Yes (peer relationship) | Yes (node0/node1) | Yes (peer/HA partner) |
| Configuration Scope<br>(must match, if synced will match) | Full<br>(single running config for logical switch) | Full | Full | Partial | Majority | Majority |
| Configuration Sync<br>(full / majority / independent) | Full | Full | Full | Independent | Majority<br>(minor local config) | Majority<br>(minor local config) |
| Redundancy Group Identifier | Domain/Pair ID | Stack/Chassis ID | Cluster ID | Domain/Pair ID<br>(vPC domain ID / MLAG domain) | Cluster ID | HA/Cluster ID |
| Redundancy Mode | Active/Active | Active/Active | Active/Active or Active/Standby | Active/Active | Active/Standby or Active/Active | Active/Standby or Active/Active |
| Dedicated HA Interface | Yes | Yes | Yes | Yes | Yes | Typically<br>(sync/heartbeat links) |
| Shared Virtual MAC | Yes | Yes | Yes | Typically<br>(via protocol such as FHRP/anycast) | Yes (on L3) | Yes |


1. Dual-chassis Single Control Plane
    VSS / StackWise Virtual (Cisco)
2. Multi-chassis Stack
    Stackwise / Virtual Chassis / Arista Stack / HPE IRF / Extreme SummitStack
3. Firewall Cluster
    Cisco FXOS / SRX
4. Multi-chassis L2 Pair
    VPC / MLAG (Cisco vPC, Arista MLAG, Juniper MC-LAG variants)
5. Firewall HA pairs
    PAN / Fortinet / ASA
6. HA Pairs
    Load balancer HA / F5 BIG-IP HA / A10 Thunder HA / Viptela / Versa / Silver Peak

The primary piece of information to consider from this list is the Management Control Plane Count. When it is **one** you should use a VirtualChassis and when it is **two**, you should use a Device Redundancy Group.

## Virtual Chassis

### Nautobot Model Overview

TODO: Insert UML here

**VirtualChassis Attributes**

| Attribute | Type | Required | Description |
|---|---|---|---|
| `name` | String | Yes | Unique name identifying the virtual chassis |
| `master` | FK → Device | No | The device that acts as the control plane master for the chassis; all member devices are managed through this device |
| `domain` | String | No | Optional domain name shared across chassis members (used in some vendor implementations for identification) |

**Device Attributes (virtual chassis-related)**

| Attribute | Type | Required | Description |
|---|---|---|---|
| `virtual_chassis` | FK → VirtualChassis | No | The virtual chassis this device belongs to |
| `vc_position` | Integer (0–255) | Yes (if in VC) | Slot/position of this device within the virtual chassis; must be unique per chassis |
| `vc_priority` | Integer (0–255) | No | Election priority for master role; higher values win (vendor behavior varies) |

### Sample API
### Sample Design Builder
### GraphQL

===================
### Dual-chassis Single Control Plane

#### Key Questions

- Can you port channel across multiple devices? Yes, (review bulk edit)
- Can you see all interfaces on the Primary? Yes
- Can you see all interfaces on the Backup? No, only see what is physically on that device (e.g. not the other interfaces)
- On Primary, can you tell which interfaces are assigned to which device? Yes, a column "Device" starts showing up
- When do you see all the interfaces on the master device? When it is set to master
- Can you connect interfaces from master to non-master? Yes
- Do all configuration map to the model correctly? Yes
- How are interfaces named? TODO: 
- What should the naming standard be for the chassis device?  TODO: 
- Should I use interface named templates? Yes. You will likely have to rename them after the fact, but the bulk rename makes it simple.

#### Configuration Generation

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


### Multi-Chassis Stack

#### Key Questions

These questions and answers are based on **Cisco StackWise**:

Q. Can you port channel across multiple devices? Yes (this is called a Multi-Chassis EtherChannel or MEC).
Q. Can you see all interfaces on the Primary? Yes.
Q. Can you see all interfaces on the Backup? Yes (the standby maintains a synced control plane).
Q. On Primary, can you tell which interfaces are assigned to which device? Yes (via the interface naming convention).
Q. When do you see all the interfaces on the master device? Always (once the stack is formed and members are "Ready").
Q. Can you connect interfaces from master to non-master? Yes.
Q. Any configurations don't map back to model? No (configurations are applied to the logical stack, not specific physical hardware models).
Q. How are interfaces named? Interface Type Stack-Unit/Slot/Port (e.g., GigabitEthernet 1/0/1).
Q. What should the naming standard be for the chassis device? Member numbers (usually 1 through 8 or 9).
Q. Should I use interface named templates? Yes (highly recommended for consistency across the stack).

#### Configuration Generation

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

#### Key Questions

- Can you port channel across multiple devices? Yes — spanned EtherChannel is supported in FTD clustering
- Can you see all interfaces on the Primary (control node)? No — Each node can only see its interfaces, but all cluster interfaces are visible via FMC
- Can you see all interfaces on the Backup (data node)? No — only interfaces physically on that chassis module are visible locally
- On Primary, can you tell which interfaces are assigned to which device? No — Only the FMC can see all interfaces
- When do you see all the interfaces on the master device? You cannot - Only the FMC can see all interface
- Can you connect interfaces from master to non-master? Yes
- Do all configurations map to the model correctly? Mostly Yes - Anything not represented in the model can be stored in the config context
- How are interfaces named? FXOS notation (e.g., `Ethernet1/1`, `Ethernet1/2`) at chassis level; logical names assigned in FMC
- What should the naming standard be for the chassis device? Use the shared cluster name / FMC display name (logical single name)
- Should I use interface named templates? Yes

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






## Device Redundancy Groups

### Nautobot Model Overview

TODO: Insert UML here

**DeviceRedundancyGroup Attributes**

| Attribute | Type | Required | Description |
|---|---|---|---|
| `name` | String | Yes | Unique name identifying the redundancy group |
| `status` | Status | Yes | Lifecycle status of the group (e.g., Planned, Active, Decommissioning) |
| `description` | String | No | Brief human-readable description of the group's purpose |
| `failover_strategy` | Choice | No | How traffic is handled across members: `Active/Active` (both units process traffic simultaneously) or `Active/Passive` (one unit is standby until failover occurs) |
| `comments` | Text | No | Free-form notes about the group |
| `secrets_group` | FK → SecretsGroup | No | Credentials used to access devices in this group (e.g., shared enable password) |

**Device Attributes (redundancy-related)**

| Attribute | Type | Required | Description |
|---|---|---|---|
| `device_redundancy_group` | FK → DeviceRedundancyGroup | No | The redundancy group this device belongs to |
| `device_redundancy_group_priority` | Integer (≥ 1) | No | Priority of this device within the group; lower values indicate higher priority (e.g., `1` = primary) |

### Sample API
### Sample Design Builder
### GraphQL

================

### Multi-chassis L2 Pair TODO: Ken
#### Key Questions
#### Configuration Generation





### Firewall HA pair

#### Key Questions

- Can you port channel across multiple devices? No — EtherChannel is per-device only
- Can you see all interfaces on the Primary? No — the active unit only shows its own interfaces #TODO: Is this really asking "Can all phyical and logical interfaces on both devices be configured on the primary?
- Can you see all interfaces on the Backup? No — the standby unit has its own separate interface list
- On Primary, can you tell which interfaces are assigned to which device? N/A — each device is modeled separately in Nautobot
- When do you see all the interfaces on the master device? Each device always shows only its own interfaces
- Can you connect interfaces from master to non-master? The failover and stateful link interfaces connect the two units either directly or via a switch
- Do all configurations map to the model correctly? Mostly yes; standby IPs and failover link require HA-specific handling
- How are interfaces named? Standard ASA format (e.g., `GigabitEthernet0/0`, `Management0/0`)
- What should the naming standard be for the HA pair? A combination of the two devices names (e.g., `ASA01/ASA02` for `ASA01` and `ASA02`)
- Should I use interface named templates? Yes

#### Configuration Generation

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

> Note: Standby IP is assigned to the secondary unit's corresponding interface automatically

_Secondary (Standby) Unit — Failover Config_

```
failover
failover lan unit secondary
failover lan interface FAILOVER GigabitEthernet0/3
failover link STATEFUL GigabitEthernet0/4
failover interface ip FAILOVER 10.1.1.1 255.255.255.252 standby 10.1.1.2
failover interface ip STATEFUL 10.1.2.1 255.255.255.252 standby 10.1.2.2
```

> Note: The secondary unit receives the full running config from the primary after the failover link is established; interface IPs need not be set manually






### HA pairs


#### Key Questions

These questions and answers are based on **F5 BIG-IP (DSC)**:

Q. Can you port channel across multiple devices? No. (Each device must have its own independent trunks/links to the switches)
Q. Can you see all interfaces on the Primary? No. (You only see the local physical interfaces of the Primary unit)
Q. Can you see all interfaces on the Backup? No. (You only see the local physical interfaces of the Backup unit).
Q. On Primary, can you tell which interfaces are assigned to which device? No. (The Primary is unaware of the Backup's specific physical port numbering).
Q. When do you see all the interfaces on the master device? Never. (They remain two separate hardware entities).
Q. Can you connect interfaces from master to non-master? No. (There is no "backplane" traffic switching; you only connect them via HA/Sync cables)
Q. Any configurations don't map back to model? Yes. (Specific items like Management IP, Hostname, and Interface speeds are "Device-Specific" and do not sync).
Q. How are interfaces named? Slot.Port (e.g., 1.1, 1.2).
Q. What should the naming standard be for the chassis device? FQDN (e.g., f5-01.network.local).
Q. Should I use interface named templates? No. (F5 uses VLAN names to abstract the configuration; you sync the VLAN, not the interface).

#### Configuration Generation

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

1. Device A (Primary)

```
modify sys global-settings mgmt-dhcp disabled
create sys management-ip 192.168.1.10/24

create net self floating_mgmt_ip { address 192.168.1.12/24 vlan internal floating enabled traffic-group traffic-group-1 }
```

# Device B (Standby)

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
