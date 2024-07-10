# Cloud Services

Cloud services in Nautobot offer a way to track resources, applications, and data storage made available to users via remote servers. Common cloud services are Amazon Web Services (AWS), Google App Engine, Microsoft Azure Virtual Machines, and etc. Each cloud service must be assigned to a [cloud type](./cloudtype.md) and a [cloud network](./cloudnetwork.md) and can be optionally assigned to a [cloud account](./cloudaccount.md). Extra configurations can be stored in JSON format in the `extra_config` attribute.
