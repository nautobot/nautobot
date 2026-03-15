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
TODO: Insert Model table summarizing attributes and their meanings

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

### Firewall Cluster TODO: Allen
#### Key Questions
#### Configuration Generation






## Device Redundancy Groups

### Nautobot Model Overview

TODO: Insert UML here

TODO: Insert Model table summarizing attributes and their meanings

### Sample API
### Sample Design Builder
### GraphQL

================

### Multi-chassis L2 Pair TODO: Ken
#### Key Questions
#### Configuration Generation





### Firewall HA pair TODO: Allen
#### Key Questions
#### Configuration Generation






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
