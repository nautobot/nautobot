# Cloud Services

In Nautobot, cloud services enable tracking of resources, applications, and data storage provided to users via remote servers. A cloud service represents a specific instance of a service defined by its [cloud resource type](./cloudresourcetype.md). For example, it could describe an EC2 instance of type "c7gn.xlarge" from Amazon EC2 or a Linux virtual machine instance of type "M416ms_v2" created using Microsoft Azure Virtual Machine Service within the user's virtual private cloud.

Each cloud service must be assigned to a [cloud resource type](./cloudresourcetype.md) and can optionally be assigned to a [cloud account](./cloudaccount.md) and zero or more [cloud networks](./cloudnetwork.md). When a cloud account is assigned, the cloud resource type must have the same provider as the cloud account. Extra configurations can be stored in JSON format in the `extra_config` attribute.

!!! note
    Note that a [cloud network](./cloudnetwork.md) already has a [cloud account](./cloudaccount.md) associated with it. So in some cases, the `cloud_account` attribute of cloud service instances can be left blank. You can assign a cloud account to a cloud service to handle any case where the service belongs to a different account than its associated network(s).

A cloud service can optionally be assigned to a [cloud resource group](./cloudresourcegroup.md). In that case, the cloud service must also be assigned to the cloud account that the cloud resource group belongs to.

The name of each cloud service must be unique within its cloud account and cloud resource group. An empty cloud account or cloud resource group counts as a scope of its own, so two cloud services without a cloud account cannot share a name.

The identifier assigned to a cloud service by the provider, such as an Azure resource ID, an AWS ARN or a GCP resource name, can be recorded in the `provider_resource_id` field. When set, it must be unique among cloud services.

Each cloud service must be assigned an operational [`status`](../../platform-functionality/status.md). The following statuses are available by default:

- Planned
- Active
- Decommissioning

A cloud service can also be assigned a functional [`role`](../../platform-functionality/role.md), a [tenant](../tenancy/tenant.md) and a [location](../dcim/location.md), such as the cloud region that the service is deployed in. The [location type](../dcim/locationtype.md) of the location must permit the cloud service content type.

+++ 3.3.0
    The `cloud_resource_group`, `provider_resource_id`, `location`, `status`, `role`, `tenant` and `ip_addresses` fields have been added. Existing cloud services are set to the "Active" status when upgrading. VPN tunnel endpoints can now be attached to a cloud service, and the detail view of a cloud service lists its virtual servers and VPN tunnel endpoints.

+/- 3.3.0
    Cloud service names were previously unique across all cloud services. They are now unique within their cloud account and cloud resource group. In addition, the cloud resource type of a cloud service with a cloud account must now have the same provider as that cloud account.

## IP Addresses

Zero or more [IP addresses](../ipam/ipaddress.md) can be assigned to a cloud service, for addresses that a managed service consumes in a cloud network or on the internet. Examples are the private IP address of a private endpoint, the address of a managed database or the public IP addresses of a NAT gateway. This many to many relationship is represented by [the CloudServiceIPAddressAssignment model](./cloudserviceipaddressassignment.md). IP addresses can be filtered by the cloud services they are assigned to with the `cloud_services` filter.

## Related Objects

A cloud service can be referenced by other objects in Nautobot:

- A [virtual server](../load-balancers/virtualserver.md) can be attached to a cloud service that represents a cloud load balancer.
- A [VPN tunnel endpoint](../vpn/vpntunnelendpoint.md) can be attached to a cloud service that represents a cloud VPN gateway.

The detail view of a cloud service lists the virtual servers and VPN tunnel endpoints attached to it, when there are any.
