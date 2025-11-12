# Load Balancer Pool

## Overview

A load balancer pool is a group of servers that work together to distribute incoming traffic efficiently, ensuring high availability, scalability, and optimal resource utilization for an application or service.

The load balancer pool model provides the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique name for the load balancer pool. |
| `load_balancing_algorithm` | choice | Yes | Load balancing strategy (e.g., Round Robin, Least Connections). Valid choices can come from netutils or Constance `load_balancing_algorithms`. |
| `health_check_monitor` | ForeignKey to HealthCheckMonitor | No | Optional monitor used to check the health of pool members. Must exist before assignment. |
| `tenant` | ForeignKey to Tenant | No | Optional tenant ownership. |

## Details

The `LoadBalancerPool` model defines a group of backend nodes that serve traffic distributed by one or more Virtual Servers. Each pool consists of one or more Pool Members and may include optional health monitoring.

Pools act as the target destinations for Virtual Servers, enabling load balancing logic such as round robin or least connections to be applied to a set of backend servers.

- Load Balancer Pool Members must be created separately and assigned to the pool.
- Health Check Monitor must exist before it can be linked to a pool.
- Pools may exist without being attached to a Virtual Server.
- A Load Balancer Pool can be defined and saved without being attached to a Virtual Server.
- A pool must have at least one Load Balancer Pool Member to be considered functionally complete for most use cases.
