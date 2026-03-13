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






### HA pairs TODO: Jeff

The SRX uses a concept called a **Chassis Cluster**, where two discrete SRX devices are logically merged into a single, unified system. The two nodes communicate over a dedicated **Control Link** (for heartbeat, state synchronization, and configuration) and a **Fabric Link** (for data plane forwarding between nodes). From a management perspective, the pair looks like one device with a single configuration and a single routing engine. One node is always the **primary** (actively processing traffic and running routing protocols) and the other is the **secondary** (standby), though you can influence which interfaces are active on which node using **Redundancy Groups (RGs)**. RG0 always controls the routing engine mastership, while RG1 and above control data plane interfaces. This means you can achieve a form of **active/active** by splitting traffic across RGs, though each individual RG is still in an active/passive relationship. Session state is synchronized across the fabric link in real time, enabling stateful failover.

Control/Mgmt/Fabric ports: https://www.juniper.net/documentation/us/en/software/junos/chassis-cluster-security-devices/topics/concept/chassis-cluster-srx-series-node-interface-understanding.html#cc_node_intf_gateway__section_wbq_sjw_l2c




#### Key Questions

Q. Can you port channel across multiple devices? n/a (i think)
Q. Can you see all interfaces on the Primary? Yes, but in chassis model they get renumbered ... hard to solve. (Feel like device-type for SRX1500-HA-Mode) which just has them would make sense.
Q. Can you see all interfaces on the Backup? Yes, configurations are shared / synced same as above.
Q. On Primary, can you tell which interfaces are assigned to which device? Yes
Q. When do you see all the interfaces on the master device? show interfaces
Q. Can you connect interfaces from master to non-master? yes
Control Port (some times dedicated (ctl), other Juniper provide specific ethernet port to use ie ge-0/0/1)
Fabric Port (user defined)
Q. Any configurations don't map back to model? None found
Q. How are interfaces named?
(node0) is front panel names == names in show commands
(node1) front panel names != names in show commands
In chassis cluster mode node1 gets renumbers where the first numer in the naming ie. (ge-5) is N+1 where the node0 naming ended.  Typically based on chassis/linecards etc.
Q. What should the naming standard be for the chassis device?
Device 1: srx1500-node0
Device 2: srx1500-node1
DRG: srx1500-rg-#??

    * Since there is n number of Juniper redundancy-group

Q. Should I use interface named templates?
yes, but manually determine the n+1 for proper numbering.

Other oddities: 

* SRX priority higher is preferred which is opposite of NB default device redundancy group priority?
* SRX bases off of n- redundancy groups.  Which allows certain traffic to be active on one and others active on the other. (multiple device redundancy group in NB make sense?)

Once chassis cluster mode is set on both nodes and they’re rebooted the configuration is synced and anything done on node0 or node1 automatically syncs.


#### Configuration Generation

```
## On Node0
set chassis cluster cluster-id 1 node 0 reboot

## On Node1
set chassis cluster cluster-id 1 node 1 reboot
```

Important: Once chassis cluster mode is syncing the node1 interface names change (based on chassis type model type etc). In the example below ge-5 is actually the ge-0 on node1.


```
## Setup Fabric Ports (syncs session information between systems) (userdefined ge interface)
set interfaces fab0 fabric-options member-interfaces ge-0/0/2
set interfaces fab1 fabric-options member-interfaces ge-5/0/2

## Connect control port between devices (usually dedicate ctl port but sometimes not)
## -- no config for this -- auto happens when reboot into chassis cluster happens.

# redundancy-group 0 is for route-engine all others are user defined for user traffic.
set chassis cluster redundancy-group 1 node 0 priority 150
set chassis cluster redundancy-group 1 node 1 priority 100
set chassis cluster redundancy-group 1 preempt
set chassis cluster redundancy-group n+1 node 0 priority 150
set chassis cluster redundancy-group n+1 node 1 priority 100
set chassis cluster redundancy-group n+1 preempt

## General Data plane PreReq
set interfaces reth0 unit 0 family inet address 90.90.90.1/24
set interfaces reth1 unit 0 family inet address 10.1.1.1/24
set interfaces ge-0/0/14 gigether-options redundant-parent reth0
set interfaces ge-0/0/15 gigether-options redundant-parent reth1
set interfaces ge-5/0/14 gigether-options redundant-parent reth0
set interfaces ge-5/0/15 gigether-options redundant-parent reth1

## Assign Zones to Reths
set security zones security-zone untrust interface reth0.0
set security zones security-zone trust interface reth1.0

## Each redundancy-group is configured with a “weight value” of 255 by default.
## Junos can monitor the state of certain interfaces, and if those interfaces go down
## it can lower the group’s weight value to whatever you like.
## When the weight value reaches 0, the failover happens.
set chassis cluster redundancy-group 1 interface-monitor ge-0/0/14 weight 255
```

Firewall 1 (Node1)

Nothing beside the initial cluster chassis “enablement” is needed.








