# VPN Data Models

Nautobot provides a set of models for representing Virtual Private Networks (VPNs), including reusable profiles, policies, and tunnel endpoints. These models enable you to define IKE (Phase 1) and IPSec (Phase 2) policy parameters, manage tunnel endpoints, and associate VPNs with tenants, roles, and secrets.

!!! note
    At present, Nautobot's VPN models are designed to represent tunnel-based VPNs. Support for overlay VPNs (MPLS, VXLAN, etc) is planned for future releases.

## High-Level Architecture of VPN Models

The following diagram represents the logic behind VPN Models at a high level.
![VPN Models](../../../media/models/vpn_models_high_level_light.png#only-light)
![VPN Models](../../../media/models/vpn_models_high_level_dark.png#only-dark)

## Entity Relationship Diagrams

The following schemas illustrate the connections between related models.

!!! note
    Two separate diagrams are shown to make it easier for the reader. Additionally, several minor elements such as Status and Role are not shown for the same reason.

### VPN Profile Models Entity-Relationship Diagram

```mermaid
---
title: VPN Profile, Phase I, and Phase II Policies
---
erDiagram
    "extras.Role"[Role] {}
    "extras.SecretsGroup"[SecretsGroup] {}
    "nautobot_vpn_models.VPN"[VPN] {}
    "nautobot_vpn_models.VPNTunnel"[VPNTunnel] {}
    "nautobot_vpn_models.VPNTunnelEndpoint"[VPNTunnelEndpoint] {}


    "nautobot_vpn_models.VPNProfile"[VPNProfile] {
        VPNPhase1Policy vpn_phase1_policy FK "Phase 1 Policy"
        VPNPhase2Policy vpn_phase2_policy FK "Phase 2 Policy"
        string name UK "Name"
        string description "Description"
        boolean keepalive_enabled "Keepalive enabled"
        integer keepalive_interval "Keepalive interval"
        integer keepalive_retries "Keepalive retries"
        boolean nat_traversal "NAT traversal"
        json extra_options "Extra options"
        SecretsGroup secrets_group FK
        Role role FK "Role"
    }

    "nautobot_vpn_models.VPNPhase1Policy"[VPNPhase1Policy] {
        string name UK "Name"
        string description "Description"
        choices ike_version "IKEv1, IKEv2"
        boolean aggressive_mode "Use aggressive mode"
        choices encryption_algorithm "AES-256-GCM, AES-256-CBC, AES-192-GCM, AES-192-CBC, AES-128-GCM, AES-128-CBC, 3DES, DES"
        choices integrity_algorithm "SHA512, SHA384, SHA256, SHA1, MD5"
        choices dh_group "Diffie-Hellman group"
        integer lifetime_seconds "Lifetime in seconds"
        integer lifetime_kb "Lifetime in kiolbytes"
        choices authentication_method "PSK, RSA, ECDSA, Certificate"
    }

    "nautobot_vpn_models.VPNPhase2Policy"[VPNPhase2Policy] {
        string name UK "Name"
        string description "Description"
        choices encryption_algorithm "AES-256-GCM, AES-256-CBC, AES-192-GCM, AES-192-CBC, AES-128-GCM, AES-128-CBC, 3DES, DES"
        choices integrity_algorithm "SHA512, SHA384, SHA256, SHA1, MD5"
        choices pfs_group "Perfect Forward Secrecy group"
        integer lifetime "Lifetime in seconds"
    }

    "nautobot_vpn_models.VPNProfile" }o--o{ "nautobot_vpn_models.VPNPhase1Policy" : "may have"
    "nautobot_vpn_models.VPNProfile" }o--o{ "nautobot_vpn_models.VPNPhase2Policy" : "may have"
    "nautobot_vpn_models.VPNProfile" }o--o| "extras.Role" : "may have"
    "nautobot_vpn_models.VPNProfile" }o--o| "extras.SecretsGroup" : "may have"

    "nautobot_vpn_models.VPN" }o--o| "nautobot_vpn_models.VPNProfile" : "may have"
    "nautobot_vpn_models.VPNTunnel" }o--o| "nautobot_vpn_models.VPNProfile" : "may have"
    "nautobot_vpn_models.VPNTunnelEndpoint" }o--o| "nautobot_vpn_models.VPNProfile" : "may have"
```

### VPN Models Entity-Relationship Diagram

```mermaid
---
title: VPNs, Tunnels, and Endpoints
---
erDiagram
    "dcim.Interface"[Interface] {}
    "extras.DynamicGroup"[DynamicGroup] {}
    "ipam.IPAddress"[IPAddress] {}
    "ipam.Prefix"[Prefix] {}
    "tenancy.Tenant"[Tenant] {}
    "extras.ContactAssociations"[ContactAssociations] {}

    "nautobot_vpn_models.VPN"[VPN] {
        VPNProfile vpn_profile FK "VPN Profile"
        string name UK "Name"
        string description "Description"
        string vpn_id "VPN ID"
        Tenant tenant FK "Tenant"
        Role role FK "Role"
        ContactAssociations contact_associations FK "Contact Associations"
    }

    "nautobot_vpn_models.VPNTunnel"[VPNTunnel] {
        VPNProfile vpn_profile FK "VPN Profile"
        VPN vpn FK,UK "VPN"
        string name UK "Name"
        string description "Description"
        string tunnel_id "Tunnel ID"
        choices encapsulation "IPsec - Transport, IPsec - Tunnel, IP-in-IP, GRE, WireGuard, L2TP, PPTP, OpenVPN, EoIP"
        Tenant tenant FK "Tenant"
        Status status FK "Status"
        Role role FK "Role"
        ContactAssociations contact_associations FK "Contact Associations"
    }

    "nautobot_vpn_models.VPNTunnelEndpoint"[VPNTunnelEndpoint] {
        VPNProfile vpn_profile FK "VPN Profile"
        VPNTunnel vpn_tunnel FK,UK "VPN Tunnel"
        IPAddress source_ipaddress FK,UK "Source IP Address"
        Interface source_interface FK "Source Interface"
        IPAddress destination_ipaddress FK "Destination IP Address"
        string destination_fqdn "Destination FQDN"
        Interface tunnel_interface FK "Tunnel Interface"
        DynamicGroup protected_prefixes_dg FK "Protected Prefixes in Dynamic Groups"
        Prefix protected_prefixes FK "Protected Prefixes"
        Role role FK "Role"
        ContactAssociations contact_associations FK "Contact Associations"
    }

    "nautobot_vpn_models.VPN" }o--o| "tenancy.Tenant" : "may have"
    "nautobot_vpn_models.VPN" }o--o{ "extras.ContactAssociations" : "may have"

    "nautobot_vpn_models.VPNTunnel" }o--o| "nautobot_vpn_models.VPN" : "may have"
    "nautobot_vpn_models.VPNTunnel" }o--o| "tenancy.Tenant" : "may have"
    "nautobot_vpn_models.VPNTunnel" }o--o{ "extras.ContactAssociations" : "may have"

    "nautobot_vpn_models.VPNTunnelEndpoint" }o--o{ "nautobot_vpn_models.VPNTunnel" : "may have"
    "nautobot_vpn_models.VPNTunnelEndpoint" }o--o| "ipam.IPAddress" : "destination_ipaddress"
    "nautobot_vpn_models.VPNTunnelEndpoint" }o--o| "ipam.IPAddress" : "source_ipaddress"
    "nautobot_vpn_models.VPNTunnelEndpoint" }o--o| "dcim.Interface" : "source_interface"
    "nautobot_vpn_models.VPNTunnelEndpoint" |o--o| "dcim.Interface" : "tunnel_interface"
    "nautobot_vpn_models.VPNTunnelEndpoint" }o--o{ "extras.DynamicGroup" : "protected_prefixes_dg"
    "nautobot_vpn_models.VPNTunnelEndpoint" }o--o{ "ipam.Prefix" : "protected_prefixes"
    "nautobot_vpn_models.VPNTunnelEndpoint" }o--o{ "extras.ContactAssociations" : "may have"
```

## Indicative Usage

### Use Cases

#### Site-to-site IPSec VPN tunnel (transport mode)

Probably the simplest scenario for creating an IPSec VPN tunnel between two endpoints. No tunnel interface is assumed in this scenario.
![VPN Models](../../../media/models/vpn_models_use_case_01_light.png#only-light)
![VPN Models](../../../media/models/vpn_models_use_case_01_dark.png#only-dark)

#### Site-to-site IPSec VPN tunnel (tunnel mode)

Another scenario with an IPSec VPN tunnel between two endpoints but this time a tunnel interface is used.
![VPN Models](../../../media/models/vpn_models_use_case_02_light.png#only-light)
![VPN Models](../../../media/models/vpn_models_use_case_02_dark.png#only-dark)

#### Single hub-and-spoke VPN

Implementation of a hub-and-spoke topology (e.g. DMVPN) with RTR99 as the hub. The difference between this and site-to-site VPN tunnels is that, in this case, the hub only receives inbound VPN requests from the spokes. As such, its tunnel endpoint is re-used among tunnels and also does not need to define destination IP/FQDN.
![VPN Models](../../../media/models/vpn_models_use_case_03_light.png#only-light)
![VPN Models](../../../media/models/vpn_models_use_case_03_dark.png#only-dark)

#### Multiple hub-and-spoke VPNs

Virtually the same as above, mentioned here to illustrate the separation between VPN groupings.
![VPN Models](../../../media/models/vpn_models_use_case_04_light.png#only-light)
![VPN Models](../../../media/models/vpn_models_use_case_04_dark.png#only-dark)

### GraphQL query examples

The following GraphQL query examples show how an operator can query the information that is stored in the proposed VPN models.

#### Querying VPN attributes

```json
{
  vpns {
    vpn_profile {
      name
      secrets_group {
        name
      }
      vpn_phase1_policies {
        name
        encryption_algorithm
        integrity_algorithm
      }
      vpn_phase2_policies {
        name
        encryption_algorithm
        integrity_algorithm
      }
    }
    vpn_tunnels {
      name
      vpn_profile {
        name
      }
    }
  }
}
```

#### Device-level VPN info

```json
{
  device (id: "ABC123") {
    name
    vpn_tunnel_endpoints {
      endpoint_a_vpn_tunnels {
        name
        tunnel_id
        vpn_profile {
          name
        }
      }
      endpoint_z_vpn_tunnels {
        name
        tunnel_id
        vpn_profile {
          name
        }
      }
    }
  }
}
```

### Questions to ask of the data model

Given the data model, what questions would a user ask?

- Given a device, I would like to know all the Tunnels associated with it
- Given a tunnel, I would like to know all peers associated with it e.g. the remote devices
- Given a tunnel or device, I would like to know what tunnel technology I am using e.g. GRE vs DMVPN
- Given a DMVPN tunnel, I would like to know whether I am a hub or a spoke
- Given a DMVPN tunnel, I would like to know if I can directly route between spokes i.e. DMVPN phase 3
- Given a Tunnel, I would like to know, which subnets are considered “southbound” of that
- Given a Tenant, what VPN Tunnel would have to be configured
