# Cloud Services

In Nautobot, cloud services enable tracking of resources, applications, and data storage provided to user via remote servers. A cloud service represents a specific instance, within a user's [cloud network](./cloudnetwork.md), of a service defined by its [cloud type](./cloudtype.md). For example, it could describe an EC2 instance of type "c7gn.xlarge" from Amazon EC2 or a Linux virtual machine instance of type "M416ms_v2" created using Microsoft Azure Virtual Machine Service within the user's virtual private cloud.

Each cloud service must be assigned to a [cloud type](./cloudtype.md) and a [cloud network](./cloudnetwork.md) and can be optionally assigned to a [cloud account](./cloudaccount.md). Extra configurations can be stored in JSON format in the `extra_config` attribute.

!!! note
    Note that a [cloud network](./cloudnetwork.md) already has a [cloud account](./cloudaccount.md) associated with it. So in most cases, the `cloud_account` attribute of cloud service instances can be left blank. You can assign a cloud account to a cloud service to handle any case where the service belongs to a different account than its associated network.
