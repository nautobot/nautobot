# Interface Redundancy Groups

+++ 1.6.0

Interface Redundancy Groups represent groups of interfaces that share a single virtual address. This model is intended to represent redundancy protocols such as HSRP or VRRP that allow multiple devices to provide a fault-tolerant default gateway for a network.

Interface Redundancy Groups must be created before interfaces can be assigned to the group.

!!! note
    While Interface Redundancy Groups were designed to represent first hop redundancy protocols, they may be used to represent any grouping of redundant interfaces.

## Required Fields

When adding Interfaces to the Interface Redundancy Group, a priority integer value must be set for each interface in the group. This value will depend on the redundancy protocol being used. For example, HSRP uses a priority value between 1 and 255.

## Optional Fields

An IP Address can be related to an Interface Redundancy Group, which will be used as the virtual address for the group.

Redundancy protocol can be set on the group. Supported redundancy protocols are: HSRP, VRRP, GLBP and CARP.

Secrets groups can be used to store secret information used by the redundancy protocol. An example use case would be an HSRP authentication key.

Protocol group ID stores the group identifier (HSRP group ID or VRRP group ID, etc.) as an integer or text label up to 50 characters long.
