# Virtual Device Context (VDC)

+++ 2.4.0

A Virtual Device Context (VDC) refers to a logical partition of a physical network device, allowing it to function as multiple independent devices. Each VDC operates separately, with its own configuration, interfaces, and IP addresses. VDCs are particularly useful for multi-tenant environments, where different customers or applications require isolated configurations.

VDCs are created first before interfaces can be assigned to them, and each VDC can efficiently share the physical resources of a device while retaining its own operational independence. This enables enhanced scalability and flexibility in network setups.

## Overview

Virtual Device Contexts (VDCs) allow a single physical device to be divided into multiple virtual instances, each functioning independently. They enable network administrators to separate operational environments within a single piece of hardware, which is beneficial for organizations that need distinct configurations for different departments, customers, or applications.

Each VDC can be assigned its own roles, IP addresses, and configurations, providing a high level of isolation while leveraging shared resources from the underlying physical device. This can help optimize hardware utilization while maintaining the necessary separation between different environments.

## Key Features

- **Isolation**: Each VDC operates as a separate entity with its own configurations, providing isolation between different contexts.

- **Shared Resources**: VDCs share the physical device's resources, such as processing power and memory, but still function as independent units.

- **Multi-Tenant Support**: Ideal for service providers and enterprises, VDCs help create isolated environments for multiple clients on the same hardware.

- **Flexibility**: VDCs allow for flexible network management, with administrators able to define roles and assign resources based on specific requirements.

## Example Use Cases

1. **Service Providers**: VDCs enable service providers to offer isolated network environments to multiple clients while optimizing the use of hardware resources.

2. **Separate Environments**: Organizations can use VDCs to separate testing environments from production, reducing the risk of conflicts or outages.

3. **Resource Optimization**: VDCs allow for efficient resource management by dynamically allocating network resources to different contexts based on demand.


## VDC Fields Overview

| Field         | Type                                              | Description                                          |
|---------------|---------------------------------------------------|------------------------------------------------------|
| `name`        | CharField                                         | Name of the VDC.                                     |
| `device`      | ForeignKey to `dcim.Device`                       | Physical device associated with the VDC.             |
| `identifier`  | PositiveSmallIntegerField (optional)              | Unique identifier for the VDC from the platform.     |
| `status`      | StatusField                                       | Operational status of the VDC.                       |
| `role`        | RoleField (optional)                              | Role assigned to the VDC.                            |
| `primary_ip4` | OneToOneField to `ipam.IPAddress` (optional)       | Primary IPv4 address of the VDC.                     |
| `primary_ip6` | OneToOneField to `ipam.IPAddress` (optional)       | Primary IPv6 address of the VDC.                     |
| `tenant`      | ForeignKey to `tenancy.Tenant` (optional)         | Tenant associated with the VDC.                      |
| `interfaces`  | ManyToManyField through `dcim.InterfaceVDCAssignment` (optional) | Interfaces assigned to the VDC. |
| `description` | CharField (optional)                              | Description of the VDC.                              |
