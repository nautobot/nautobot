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

Q. Can you port channel across multiple devices? 
Q. Can you see all interfaces on the Primary? 
Q. Can you see all interfaces on the Backup? 
Q. On Primary, can you tell which interfaces are assigned to which device? 
Q. When do you see all the interfaces on the master device?
Q. Can you connect interfaces from master to non-master? 
Q. Any configurations don't map back to model? 
Q. How are interfaces named?
Q. What should the naming standard be for the chassis device?
Q. Should I use interface named templates?

## Vendor Implementations

While vendors offer a variety of technologies, the data model remains largely agnostic to these specifics. The following table serves as a foundation for modeling redundant devices in Nautobot.

| Row | Dual-chassis Single Control Plane<br>(VSS / StackWise Virtual) | Multi-chassis Stack<br>(StackWise / VC / Arista Stack / IRF / SummitStack) | Firewall Cluster<br>(Cisco FXOS / SRX) | Multi-chassis L2 Pair<br>(vPC / MLAG) | Firewall HA Pair<br>(PAN / Fortinet / ASA) | HA Pairs<br>(LB / F5 / A10 / Viptela / Versa / Silver Peak) |
| --- | --- | --- | --- | --- | --- | --- |
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

1. Dual-chassis single control plane (only two)
    VSS / StackWise Virtual (Cisco)
2. Multi-chassis stack
    Stackwise / Virtual Chassis / Arista Stack / HPE IRF / Extreme SummitStack
3. Multi-chassis pair
    VPC / MLAG (Cisco vPC, Arista MLAG, Juniper MC-LAG variants)
4. Firewall HA pair 
    SRX HA (Juniper chassis cluster style; conceptually similar to firewall HA)
5. Firewall HA pairs
    Firewall HA Pair (PAN / Fortinet / ASA)
6. ADC/WAN HA pairs
    Load balancer HA / F5 BIG-IP HA / A10 Thunder HA / Viptela / Versa / Silver Peak


The primary piece of information to consider from this list is the Management Control Plane Count. When it is **one** you should use a VirtualChassis and when it is **two**, you should use a Device Redundancy Group.


## Nautobot Model Overview

Note: Insert UML here
Note: Insert Model table summarizing attributes and their meanings

## Virtual Chassis

### GraphQL

===================

#### Key Questions

Q. Can you port channel across multiple devices? Yes, (review bulk edit)
Q. Can you see all interfaces on the Primary? Yes
Q. Can you see all interfaces on the Backup? No, only see what is physically on that device (e.g. not the other interfaces)
Q. On Primary, can you tell which interfaces are assigned to which device? Yes, a column "Device" starts showing up
Q. When do you see all the interfaces on the master device? When it is set to master
Q. Can you connect interfaces from master to non-master? Yes
Q. Do all configuration map to the model correctly? Yes
Q. How are interfaces named? TODO: 
Q. What should the naming standard be for the chassis device?  TODO: 
Q. Should I use interface named templates? Yes. You will likely have to rename them after the fact, but the bulk rename makes it simple.


#### Configuration Generation

_Standard Global Config_

```
!
switch virtual domain 200
  switch 1
!
```

> Note: Switch number is local, domain must match

~~~ Management Plane ~~

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


#### Sample API
#### Sample Design Builder

===================

### Multi-chassis
#### Key Questions
#### Configuration Generation
#### Sample API
#### Sample Design Builder

===================

### Firewall Cluster
#### Key Questions
#### Configuration Generation
#### Sample API
#### Sample Design Builder


## Device Redundancy Groups

### GraphQL

===================

### Multi-chassis L2 Pair
#### Key Questions
#### Configuration Generation
#### Sample API
#### Sample Design Builder

===================

### Firewall HA pair
#### Key Questions
#### Configuration Generation
#### Sample API
#### Sample Design Builder

===================

### HA pairs
#### Key Questions
#### Configuration Generation
#### Sample API
#### Sample Design Builder

