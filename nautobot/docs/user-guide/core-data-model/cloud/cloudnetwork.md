# Cloud Networks

Cloud networks in Nautobot refer to the interconnected infrastructure and communication pathways that enable data transmission and access to [cloud services](./cloudservice.md). Common cloud networks are Amazon/Google virtual private clouds (VPCs), Azure virtual networks, multi-cloud networks, etc.

Each cloud network must have a unique name and must be assigned to a [cloud resource type](./cloudresourcetype.md) and a [cloud account](./cloudaccount.md). Each cloud network can also be linked to a parent cloud network that is not a child of other cloud networks. One or more [prefixes](../ipam/prefix.md) can be optionally assigned to cloud networks, and this many to many relationship is represented by [the CloudNetworkPrefixAssignment model](./cloudnetworkprefixassignment.md).
