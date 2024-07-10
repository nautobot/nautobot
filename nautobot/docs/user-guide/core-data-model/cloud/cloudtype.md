# Cloud Types

Cloud type in Nautobot offers a way to describe different type definitions and deployment options for [cloud services](./cloudservice.md). A cloud type instance also holds config schema that models what [cloud services](./cloudservice.md) instantiate. Common cloud types can be AWS Application Load Balancer, Azure Application Gateway, Google Cloud HTTP(s) and etc.

Each cloud type must have a unique name and must be assigned to a public and private cloud [provider](../dcim/manufacturer.md) (AWS, Azure, GCP, DigitalOcean and OpenStack etc). The user can also use the optional `content_types` attribute to designate which content types that the cloud type instance applies to.
