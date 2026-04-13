# VPN Termination

VPN Terminations associate a [VPN](vpn.md) service with exactly one local attachment point:

- a VLAN
- a device interface
- a virtual machine interface

This model is primarily intended for overlay and service-style VPN use cases where the `VPN` object describes the shared service and the `VPNTermination` records describe where that service is attached in the network.

For example, a VXLAN-based service can store its service-wide attributes on the `VPN` record, while individual `VPNTermination` records map that service to the relevant VLANs, switch interfaces, or VM interfaces that participate in it.

## Validation Rules

Each VPN Termination must satisfy the following rules:

- Exactly one of `vlan`, `interface`, or `vm_interface` must be set.
- A given VLAN can belong to only one VPN Termination.
- A given device interface can belong to only one VPN Termination.
- A given VM interface can belong to only one VPN Termination.
- VPNs whose service type is point-to-point are limited to two terminations.

These rules help keep the attachment model unambiguous and make it clear which local object is bound to which VPN service.

## Relationship to VPN

The [VPN](vpn.md) object stores service-wide data such as:

- the service identifier
- the service type
- status
- optional free-form service metadata

`VPNTermination` stores the local binding of that service to a single object in Nautobot. This separation keeps shared service attributes in one place while still allowing the service to be attached at multiple points in the infrastructure.

## Indicative Usage

Common examples include:

- mapping a VXLAN or VXLAN-EVPN service to a VLAN
- associating a service directly with a routed or switched device interface
- associating a service with a VM interface in a virtualized environment
