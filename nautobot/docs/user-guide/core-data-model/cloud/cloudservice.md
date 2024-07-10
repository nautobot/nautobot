# Cloud Services

In Nautobot, cloud services enable tracking of resources, applications, and data storage provided to user via remote servers. A cloud service represents a specific instance, within a user's [cloud network](./cloudnetwork.md), of a service defined by its [cloud type](./cloudtype.md). For instance, it could describe a server instance like "c7gn.xlarge" from Amazon EC2 or a Linux virtual machine instance named "M416ms_v2" created using Microsoft Azure Virtual Machine Service within the user's virtual private cloud.

Each cloud service must be assigned to a [cloud type](./cloudtype.md) and a [cloud network](./cloudnetwork.md) and can be optionally assigned to a [cloud account](./cloudaccount.md). Extra configurations can be stored in JSON format in the `extra_config` attribute.
