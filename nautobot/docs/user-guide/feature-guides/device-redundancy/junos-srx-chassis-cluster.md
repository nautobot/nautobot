# Juniper SRX Chassis Cluster

The SRX uses a concept called a **Chassis Cluster**, where two discrete SRX devices are logically merged into a single, unified system. The two nodes communicate over a dedicated **Control Link** (for heartbeat, state synchronization, and configuration) and a **Fabric Link** (for data plane forwarding between nodes). From a management perspective, the pair looks like one device with a single configuration and a single routing engine. One node is always the **primary** (actively processing traffic and running routing protocols) and the other is the **secondary** (standby), though you can influence which interfaces are active on which node using **Redundancy Groups (RGs)**. RG0 always controls the routing engine mastership, while RG1 and above control data plane interfaces. This means you can achieve a form of **active/active** by splitting traffic across RGs, though each individual RG is still in an active/passive relationship. Session state is synchronized across the fabric link in real time, enabling stateful failover.

Control/Mgmt/Fabric ports: https://www.juniper.net/documentation/us/en/software/junos/chassis-cluster-security-devices/topics/concept/chassis-cluster-srx-series-node-interface-understanding.html#cc_node_intf_gateway__section_wbq_sjw_l2c


## Configurations

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


## GraphQL


## Questions for the Data Model

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

