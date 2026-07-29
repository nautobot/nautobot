# VPN

A VPN object in Nautobot serves two complementary purposes:

1. **Tunnel-based VPNs** — A VPN can group multiple [VPN Tunnels](vpntunnel.md) that share similar characteristics (e.g. connections to AWS) or belong to the same organizational unit such as a WAN (e.g. DM-VPN).
2. **Overlay and service-style VPNs** — A VPN can represent an overlay or carrier service (e.g. VXLAN-EVPN, VPLS, E-Line) with [VPN Terminations](vpntermination.md) that bind the service to local attachment points such as VLANs, device interfaces, or VM interfaces.

When creating a VPN, users can specify a [VPN Profile](vpnprofile.md) that defines common settings and policies such as encryption methods, authentication protocols, and keepalive parameters.

!!! warning
    VPN Profiles assigned to VPNs are not automatically inherited by associated VPN Tunnels. At the moment, it remains the user's responsibility to decide how to use and consume this feature in their configuration templates. We consider introducing an inheritance mechanism in a later version that will make VPN Profiles even easier to use.

![VPN Detail View](../../../media/models/vpn_models_vpn_detail_light.png#only-light){ .on-glb }
![VPN Detail View](../../../media/models/vpn_models_vpn_detail_dark.png#only-dark){ .on-glb }
[//]: # ("`/vpn/vpns/<id>/`")

+++ 3.1.0
    The `service_type`, `status`, `extra_attributes` fields and support for [VPN Terminations](vpntermination.md) were added.

## Service Type

The optional `service_type` field classifies the VPN service. The following service types are available, grouped by category:

| Category | Service Type | Value |
|----------|-------------|-------|
| Tunnel | IPSec | `ipsec` |
| VPLS | VPWS | `vpws` |
| VPLS | VPLS | `vpls` |
| VXLAN | VXLAN | `vxlan` |
| VXLAN | VXLAN-EVPN | `vxlan-evpn` |
| EVPN | MPLS EVPN | `mpls-evpn` |
| EVPN | PBB EVPN | `pbb-evpn` |
| EVPN | EVPN VPWS | `evpn-vpws` |
| E-Line | EPL | `epl` |
| E-Line | EVPL | `evpl` |
| E-LAN | Ethernet Private LAN | `ep-lan` |
| E-LAN | Ethernet Virtual Private LAN | `evp-lan` |
| E-Tree | Ethernet Private Tree | `ep-tree` |
| E-Tree | Ethernet Virtual Private Tree | `evp-tree` |
| Other | SPB | `spb` |

The service type influences validation behavior — see [Validation Rules](#validation-rules) below.

## Extra Attributes

The `extra_attributes` field is a free-form JSON field for storing scalar service metadata that does not map to a dedicated Nautobot object. For example, it can hold provider-specific identifiers, contract references, or service parameters. It should not be used to store references to real Nautobot objects — use foreign key relationships for that purpose.

## Validation Rules

The following validation rules apply to VPNs:

- VXLAN-based service types (`vxlan`, `vxlan-evpn`) require the VPN identifier to be a numeric VNI (VXLAN Network Identifier) in the range 1 to 16,777,214.
- Point-to-point service types (`vpws`, `evpn-vpws`, `epl`, `evpl`) limit [VPN Terminations](vpntermination.md) to a maximum of two per VPN.
