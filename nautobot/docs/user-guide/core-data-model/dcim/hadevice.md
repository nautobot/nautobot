# HA Devices

Infrastructure is typically designed with redundancy in mind, prompting vendors to develop various technologies to support different high availability (HA) strategies. These include a range of protocols, connection types, synchronization systems, and terminology.

This creates a complex ecosystem that can be challenging to navigate, especially when determining how to model redundant infrastructure in Nautobot or which model to select. This guide aims to provide a clear and comprehensive approach to documenting HA device infrastructure by covering:

- Use Cases
- Vendor Implementations
- Data Model Overview
- GraphQL Queries
- Key questions for the data model
- Configuration stanzas
- API Calls using pynautobot snippets
- Design Builder snippets

## Use Cases

The primary use cases to consider when creating, updating, or documenting HA model protocols are:

- **Inventory Management:** Tracking assets and device details.
- **Configuration Management:** Generating and managing device configurations.
- **HA Resiliency:** Understanding and documenting network fault tolerance.

To help guide these use cases, we will ask and answer each of these questions to go with the best practices:

- Can you create a link aggregation group (LAG) across multiple devices?
- Can you see all interfaces on the Primary?
- Can you see all interfaces on the Backup?
- On a Primary object, can you tell which interfaces are assigned to which device?
- When do you see all the interfaces on the primary device?
- Can you connect interfaces from primary to non-primary?
- Do any configurations **not** map back to model?
- How are interfaces named?
- What should the naming standard be for the chassis device?
- Should I use interface named templates?

## Vendor Implementations

While vendors offer a variety of technologies, the data model remains largely agnostic to these specifics. The following table serves as a foundation for modeling redundant devices in Nautobot.

|     | Dual-chassis Single Control Plane | Multi-chassis Stack | Firewall Cluster | Multi-chassis L2 Pair | Firewall HA Pair | HA Pairs |
| --- | --- | --- | --- | --- | --- | --- |
| Example Technologies | VSS / StackWise Virtual / SRX | StackWise / VC / Arista Stack / IRF / SummitStack | Cisco FTD | vPC / MLAG / MC-LAG | PAN / Fortinet / ASA | LB / F5 / A10 / Viptela / Versa / Silver Peak |
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

### Which Nautobot Model to Use

The primary piece of information to consider from this list is the Management Control Plane Count.

- When it is **one** you should use a **VirtualChassis**.
- When it is **two**, you should use a **Device Redundancy Group**.

The rest of the documentation for the below components can be found in each data model page.

- Data Model Overview
- GraphQL Queries
- Key questions for the data model
- Configuration stanzas
- API Calls using [pynautobot](https://docs.nautobot.com/projects/pynautobot/en/latest/) snippets
- [Design Builder](https://docs.nautobot.com/projects/design-builder/en/stable/) snippets

#### Quick Navigation

- [Virtual Chassis](virtualchassis.md)
    - Arista Stack
    - Cisco VSS
    - Cisco Stackwise
    - Cisco Stackwise Virtual
    - Cisco FTD
    - HPE Intelligent Resilient Framework (IRF)
    - Juniper SRX (Chassis Cluster)
    - Extreme Networks SummitStack

- [Device Redundancy Group](deviceredundancygroup.md)
    - A10 Thunder
    - Arista MLAG
    - Aruba Silver Peak
    - Cisco ASA
    - Cisco vPC
    - Cisco Viptela | Catalyst SD-WAN Manager
    - F5 BIG-IP
    - Juniper MC-LAG
    - Versa Secure SD-WAN
