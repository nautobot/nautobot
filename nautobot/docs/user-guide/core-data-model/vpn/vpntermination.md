# VPN Termination

+++ 3.1.0
    The VPN Termination model was added to support overlay and service-style VPN use cases.

VPN Terminations associate a [VPN](vpn.md) service with exactly one local attachment point:

- a VLAN
- a device interface
- a virtual machine interface

This model is primarily intended for overlay and service-style VPN use cases where the `VPN` object describes the shared service and the `VPNTermination` records describe where that service is attached in the network.

For example, a VXLAN-based service can store its service-wide attributes on the `VPN` record, while individual `VPNTermination` records map that service to the relevant VLANs, switch interfaces, or VM interfaces that participate in it.

![VPN Termination List View](../../../media/models/vpn_models_vpntermination_list_light.png#only-light){ .on-glb }
![VPN Termination List View](../../../media/models/vpn_models_vpntermination_list_dark.png#only-dark){ .on-glb }
[//]: # ("`/vpn/vpn-terminations/`")

![VPN Termination Detail View](../../../media/models/vpn_models_vpntermination_detail_light.png#only-light){ .on-glb }
![VPN Termination Detail View](../../../media/models/vpn_models_vpntermination_detail_dark.png#only-dark){ .on-glb }
[//]: # ("`/vpn/vpn-terminations/<id>/`")

!!! note
    VPN Terminations model overlay and service-style VPN attachment points (e.g. VXLAN, VPLS, E-Line). For tunnel-based VPN endpoints (e.g. IPSec, GRE, WireGuard), see [VPN Tunnel Endpoint](vpntunnelendpoint.md) instead.

## Validation Rules

Each VPN Termination must satisfy the following rules:

- Exactly one of `vlan`, `interface`, or `vm_interface` must be set.
- A given VLAN can belong to only one VPN Termination.
- A given device interface can belong to only one VPN Termination.
- A given VM interface can belong to only one VPN Termination.
- VPNs whose [service type](vpn.md#service-type) is point-to-point (VPWS, EVPN VPWS, EPL, EVPL) are limited to two terminations.

These rules help keep the attachment model unambiguous and make it clear which local object is bound to which VPN service.

## Contextual UI Information

VPN Termination data is accessible from the following locations in the Nautobot UI:

- Under a VPN's detail view, in the **Terminations** table panel
- As a standalone list view under **VPN > VPN Terminations**

## Use Cases

Common examples include:

- mapping a VXLAN or VXLAN-EVPN service to a VLAN
- associating a service directly with a routed or switched device interface
- associating a service with a VM interface in a virtualized environment
- modeling a point-to-point E-Line (EPL/EVPL) service between exactly two device interfaces

For detailed examples with diagrams, see [Use Cases](index.md#use-cases).
