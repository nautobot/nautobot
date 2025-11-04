# Load Balancer Models

+++ 3.0.0

This section provides an overview of the data models included in Nautobot to describe load balancers. These models enable users to represent, manage, and track load balancing configurations in a vendor-neutral and infrastructure-aware manner.

Models include Virtual Servers, Load Balancer Pools, Load Balancer Pool Members, Health Check Monitors, and SSL Certificate Profiles. Several of these models integrate with other parts of Nautobot core, including IPAM (for VIPs and pool member IPs), DCIM (for device and chassis assignment), Cloud (for service mapping), and Tenancy (for tenant ownership).

## Order of Operations

When setting up objects using the Load Balancer data models, it's helpful to follow this recommended order:

1. [IP Addresses](../ipam/ipaddress.md)
2. Health Check Monitors
3. Certificate Profiles (if needed)
4. Load Balancer Pools
5. Load Balancer Pool Members (assign them to Pools)
6. Virtual Servers (link to VIPs and Pools)

This order ensures all necessary relationships and prerequisites are in place as you build your configuration.

## Models Overview

| Model Name                                    | Description |
|-----------------------------------------------|-------------|
| [Virtual Server](virtualserver.md)            | Represents a front-end VIP and port combination that distributes traffic to a backend pool. |
| [Load Balancer Pool](loadbalancerpool.md)     | A group of backend servers (Pool Members) serving traffic for a Virtual Server. |
| [Load Balancer Pool Member](loadbalancerpoolmember.md)    | An individual backend node within a Load Balancer Pool. |
| [Health Check Monitor](healthcheckmonitor.md) | Monitors the health of Pool Members and Pools to determine availability. |
| [Certificate Profile](certificateprofile.md)  | Stores metadata for SSL/TLS certificates used by Virtual Servers or Pool Members. |

## Entity Relationship Diagram

```mermaid
---
title: Load Balancer Entity Relationship Diagram
---
erDiagram
    "load_balancers.VirtualServer"[VirtualServer] {
        string name UK
        IPAddress vip FK
        int port
        choices protocol
        Prefix source_nat_pool FK
        choices source_nat_type
        choices load_balancer_type
        boolean enabled
        boolean ssl_offload
        Device device FK
        DeviceRedundancyGroup device_redundancy_group FK
        CloudService cloud_service FK
        VirtualChassis virtual_chassis FK
        Tenant tenant FK
        HealthCheckMonitor health_check_monitor FK
        CertificateProfile certificate_profiles FK
        LoadBalancerPool load_balancer_pool FK
    }

    "load_balancers.LoadBalancerPool"[LoadBalancerPool] {
        string name
        choices load_balancing_algorithm
        HealthCheckMonitor health_check_monitor FK
        Tenant tenant FK
    }

    "load_balancers.LoadBalancerPoolMember"[LoadBalancerPoolMember] {
        IPAddress ip_address FK, UK
        string label
        LoadBalancerPool load_balancer_pool FK
        Status status FK
        CertificateProfile certificate_profiles FK
        int port UK
        boolean ssl_offload
        HealthCheckMonitor health_check_monitor FK
        Tenant tenant FK
    }

    "load_balancers.HealthCheckMonitor"[HealthCheckMonitor] {
        string name
        int interval
        int retry
        int timeout
        int port
        choices health_check_type
        Tenant tenant FK
    }

    "load_balancers.CertificateProfile"[CertificateProfile] {
        string name UK
        choices certificate_type
        string certificate_file_path
        string chain_file_path
        string key_file_path
        datetime expiration_date
        string cipher
        Tenant tenant FK
    }

    "ipam.IPAddress"[IPAddress] {

    }

    "ipam.Prefix"[Prefix] {

    }

    "dcim.Device"[Device] {

    }

    "dcim.DeviceRedundancyGroup"[DeviceRedundancyGroup] {

    }

    "cloud.CloudService"[CloudService] {

    }

    "dcim.VirtualChassis"[VirtualChassis] {

    }

    "tenancy.Tenant"[Tenant] {

    }

    "load_balancers.VirtualServer" }o--|| "ipam.IPAddress" : "must have"
    "load_balancers.VirtualServer" }o--o| "ipam.Prefix" : has
    "load_balancers.VirtualServer" }o--o| "dcim.Device" : has
    "load_balancers.VirtualServer" }o--o| "dcim.DeviceRedundancyGroup" : has
    "load_balancers.VirtualServer" }o--o| "cloud.CloudService" : has
    "load_balancers.VirtualServer" }o--o| "dcim.VirtualChassis" : has
    "load_balancers.VirtualServer" }o--o| "tenancy.Tenant" : has
    "load_balancers.VirtualServer" }o--o| "load_balancers.HealthCheckMonitor" : "may have"
    "load_balancers.VirtualServer" }o--o{ "load_balancers.CertificateProfile" : "may have"
    "load_balancers.VirtualServer" }o--o| "load_balancers.LoadBalancerPool" : "may have"

    "load_balancers.LoadBalancerPool" }o--o| "load_balancers.HealthCheckMonitor" : "may have"
    "load_balancers.LoadBalancerPool" }o--o| "tenancy.Tenant" : has

    "load_balancers.LoadBalancerPoolMember" }o--|| "ipam.IPAddress" : "must have"
    "load_balancers.LoadBalancerPoolMember" }o--|| "load_balancers.LoadBalancerPool" : "must have"
    "load_balancers.LoadBalancerPoolMember" }o--o{ "load_balancers.CertificateProfile" : "may have"
    "load_balancers.LoadBalancerPoolMember" }o--o| "load_balancers.HealthCheckMonitor" : "may have"
    "load_balancers.LoadBalancerPoolMember" }o--o| "tenancy.Tenant" : has
    "load_balancers.HealthCheckMonitor" }o--o| "tenancy.Tenant" : has
    "load_balancers.CertificateProfile" }o--o| "tenancy.Tenant" : has
```

## Vendor-Specific Configuration with Custom Fields

If you need to store vendor-specific configuration elements — such as F5 iRules, persistence profiles, or application-layer settings — the recommended approach is to use [Custom Fields](../../platform-functionality/customfield.md):

- Use a **multi-select** custom field to track named elements like iRules or HTTP profiles.
- Use a **JSON** custom field to store unstructured vendor configuration snippets.
- Custom Fields can be scoped to specific object types (e.g., only `VirtualServer` or `LoadBalancerPoolMember`) to reflect how your load balancer applies these settings.

This design gives you flexibility to tailor the data model to your environment without forcing unsupported abstractions across different load balancer vendors.
