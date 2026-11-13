# Cloud Resource Types

The Cloud Resource Type model in Nautobot offers a way to describe different type definitions and deployment options for [cloud account groups](./cloudaccountgroup.md), [cloud resource groups](./cloudresourcegroup.md), [cloud networks](./cloudnetwork.md) and [cloud services](./cloudservice.md). A cloud resource type instance can include a config schema that is applied to validate the configuration of specific objects using this type. Common cloud resource types could be "AWS Application Load Balancer", "Azure Application Gateway", "Google Cloud HTTP(s)", "Azure Management Group", "Azure Resource Group", etc.

Each cloud resource type must have a unique name and must be assigned to a public or private cloud [provider](../dcim/manufacturer.md) (AWS, Azure, GCP, DigitalOcean, OpenStack, etc.). You also must populate the `content_types` attribute to designate which content types (Cloud Account Group, Cloud Resource Group, Cloud Network or Cloud Service) the cloud resource type instance applies to.

+++ 3.3.0
    Cloud resource types can also apply to cloud account groups and cloud resource groups.
