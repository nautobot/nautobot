# Cloud Networks

Cloud networks in Nautobot refer to the interconnected infrastructure and communication pathways that enable data transmission and access to [cloud services](./cloudservice.md). Common cloud networks are Amazon/Google virtual private clouds (VPCs), Azure virtual networks, multi-cloud networks, etc.

Each cloud network must have a name and must be assigned to a [cloud resource type](./cloudresourcetype.md) and a [cloud account](./cloudaccount.md). The cloud resource type must have the same provider as the cloud account. Each cloud network can also be linked to a parent cloud network that is not a child of other cloud networks, for example to model the subnets of a virtual network. A child cloud network must belong to the same cloud account as its parent. One or more [prefixes](../ipam/prefix.md) can be optionally assigned to cloud networks, and this many to many relationship is represented by [the CloudNetworkPrefixAssignment model](./cloudnetworkprefixassignment.md).

A cloud network can optionally be assigned to a [cloud resource group](./cloudresourcegroup.md), which must belong to the same cloud account as the cloud network.

The name of each cloud network must be unique within its cloud account, cloud resource group and parent cloud network. For example, two virtual networks may each have a subnet named `default`, and cloud networks in different cloud accounts or cloud resource groups may share a name. An empty cloud resource group or parent counts as a scope of its own, so two top-level cloud networks in the same cloud account without a cloud resource group cannot share a name.

The identifier assigned to a cloud network by the provider, such as an Azure resource ID, an AWS ARN or a GCP resource name, can be recorded in the `provider_resource_id` field. When set, it must be unique among cloud networks.

Each cloud network must be assigned an operational [`status`](../../platform-functionality/status.md). The following statuses are available by default:

- Planned
- Active
- Decommissioning

A cloud network can also be assigned a functional [`role`](../../platform-functionality/role.md), a [tenant](../tenancy/tenant.md) and a [location](../dcim/location.md), such as the cloud region that the network is deployed in. The [location type](../dcim/locationtype.md) of the location must permit the cloud network content type.

+++ 3.3.0
    The `cloud_resource_group`, `provider_resource_id`, `location`, `status`, `role` and `tenant` fields have been added. Existing cloud networks are set to the "Active" status when upgrading.

+/- 3.3.0
    Cloud network names were previously unique across all cloud networks. They are now unique within their cloud account, cloud resource group and parent cloud network. In addition, the cloud resource type of a cloud network must now have the same provider as its cloud account, and a child cloud network must belong to the same cloud account as its parent.
