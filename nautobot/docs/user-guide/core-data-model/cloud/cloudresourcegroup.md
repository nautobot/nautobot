# Cloud Resource Groups

+++ 3.3.0

Cloud resource groups represent containers of cloud resources inside a [cloud account](./cloudaccount.md), such as Azure resource groups. They record which container a [cloud network](./cloudnetwork.md) or [cloud service](./cloudservice.md) belongs to, which often reflects how these resources are deployed and how access to them is granted.

Each cloud resource group must have a name and must be assigned to a [cloud resource type](./cloudresourcetype.md) and to exactly one cloud account. The name of each cloud resource group must be unique within its cloud account. Extra configurations can be stored in JSON format in the `extra_config` attribute, and are validated against the config schema of the cloud resource type, if it defines one.

A cloud resource group can optionally record:

- The identifier assigned to it by the provider, such as an Azure resource ID, in the `provider_resource_id` field. When set, it must be unique among cloud resource groups.
- A [location](../dcim/location.md), such as the cloud region where the provider stores the group's metadata. The [location type](../dcim/locationtype.md) of the location must permit the cloud resource group content type.

Cloud networks and cloud services can optionally be assigned to a cloud resource group. The cloud resource group must belong to the same cloud account as the cloud network or cloud service assigned to it.
