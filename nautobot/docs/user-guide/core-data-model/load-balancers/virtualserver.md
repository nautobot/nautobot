# Virtual Server

## Overview

A virtual server is a logical service endpoint on a load balancer that distributes client requests to one or more backend servers, providing a single, consistent access point for applications.

The virtual server model provides the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the virtual server. |
| `vip` | ForeignKey to IPAddress | Conditional | IP Address where the virtual server listens. Must come from IPAM. Required unless the virtual server is attached to a cloud service. |
| `dns_name` | string | No | Optional DNS name that clients use to reach the virtual server, such as the DNS name of a cloud load balancer. |
| `port` | integer | No | Optional listening port. |
| `protocol` | choice | No | Optional protocol used. Valid choices are "TCP", "UDP", "ICMP", "SCTP", "HTTP", "HTTPS", "HTTP2", "gRPC", "QUIC", "DNS" and "ANY".|
| `source_nat_pool` | ForeignKey to Prefix | No | Optional NAT pool source prefix. Must be a valid Prefix from IPAM. |
| `source_nat_type` | choice | No | NAT type. Valid choices are "Auto", "Pool", and "Static".|
| `load_balancer_type` | choice | Yes | Indicates if this is a Layer 2, Layer 4, Layer 7, or DNS virtual server. |
| `enabled` | boolean | Yes | Whether the virtual server is active. |
| `ssl_offload` | boolean | No | Indicates SSL termination at this layer. |
| `device`, `device_redundancy_group`, `cloud_service`, `virtual_chassis` | ForeignKey | No | Optional assignment to infrastructure. Only one should be set. |
| `tenant` | ForeignKey to Tenant | No | Optional tenant assignment. |
| `health_check_monitor` | ForeignKey to HealthCheckMonitor | No | Informational or vendor-aligned health monitor reference. Must exist if used. Does not affect Pool Member health logic. |
| `certificate_profiles` | Many-to-Many to CertificateProfile | No | SSL/TLS certificate references. Should be set if SSL offload is enabled. |
| `load_balancer_pool` | ForeignKey to LoadBalancerPool | No | Pool that receives traffic from this virtual server. Must exist. |

The virtual server requires one of the following relationships to be set. This relationship is used to determine where the virtual server is configured and managed.

- `device` (Device)
- `device_redundancy_group` (DeviceRedundancyGroup)
- `virtual_chassis` (VirtualChassis)
- `cloud_service` (CloudService)

+++ 3.3.0
    The optional `dns_name` field has been added.

+/- 3.3.0
    The `vip` field is now optional for a virtual server attached to a cloud service. It is still required in every other case.

## Details

The `VirtualServer` model represents the front-end listener for client connections in a load balancing configuration. It defines the VIP (Virtual IP), port, protocol, and associations to backend pool and optional service components such as health monitors or SSL certificates.

This model is central to load balancer logic, acting as the entry point for traffic distribution to Load Balancer Pools and ultimately to Pool Members.

- Only one of `device`, `device_redundancy_group`, `cloud_service`, or `virtual_chassis` should be populated. Defining more than one can result in ambiguous associations and is not recommended.
- The `vip` field, when set, must be an existing IPAddress from the IPAM app. It is required unless `cloud_service` is set.
- If `ssl_offload` is enabled, `certificate_profiles` should be defined.
- If referencing a health check monitor, it must be created first. Note that only pool-level and member-level monitors influence backend availability decisions.
- A virtual server can be created without a pool or certificates (e.g., under construction or partially defined).

### Cloud Load Balancers

A cloud load balancer, such as an AWS Application Load Balancer, can be modeled as a virtual server attached to the [cloud service](../cloud/cloudservice.md) that represents it. Cloud load balancers are typically reached through a DNS name, and their IP addresses are managed by the cloud provider. For this reason, a virtual server attached to a cloud service does not require a `vip`, and the DNS name of the load balancer can be recorded in the `dns_name` field. The virtual servers attached to a cloud service are listed in the detail view of the cloud service.
