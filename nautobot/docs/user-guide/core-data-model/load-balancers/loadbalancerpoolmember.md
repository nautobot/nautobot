# Load Balancer Pool Member

## Overview

A load balancer pool member is an individual service within a load balancing pool that handles incoming traffic distributed by the load balancer.

The `LoadBalancerPoolMember` model provides the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ip_address` | ForeignKey to IPAddress | Yes | IP Address of the backend server. Must exist in IPAM. |
| `label` | string | No | Optional name/label for the member. |
| `load_balancer_pool` | ForeignKey to LoadBalancerPool | Yes | The pool to which this member belongs. Must exist. |
| `status` | choice | Yes | Operational status of the pool member. |
| `port` | integer | Yes | Port on which the backend server listens. Must be unique with IP. |
| `ssl_offload` | boolean | No | Indicates if SSL offload is enabled for this member. |
| `certificate_profiles` | Many-to-Many to CertificateProfile | No | SSL certificate details for this member. Should be set if SSL offload is enabled. |
| `health_check_monitor` | ForeignKey to HealthCheckMonitor | No | Optional override of the pool’s health monitor. Must exist if used. |
| `tenant` | ForeignKey to Tenant | No | Optional tenant assignment. |

## Details

The `LoadBalancerPoolMember` model represents an individual backend server within a Load Balancer Pool. Each member defines an IP Address and port where traffic will be directed by the pool, and may include SSL settings or health checks.

Pool Members are critical to load balancing operations, as they represent the actual destinations for client requests distributed by Virtual Servers through Pools.

- Must be assigned to a `LoadBalancerPool`.
- Must reference a valid `IPAddress` from Nautobot IPAM.
- May use a `HealthCheckMonitor` to override or enhance the pool-level monitor.
- May be assigned to a `Tenant`.
- Each pool member must have a unique IP Address and port combination.
- Certificate profile and health monitor are optional but recommended when `ssl_offload` is enabled.
- When `ssl_offload` is enabled, you should associate one or more `CertificateProfiles` with the member to ensure proper certificate mapping during configuration generation.
