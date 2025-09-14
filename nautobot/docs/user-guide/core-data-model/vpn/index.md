# VPN Data Models

Nautobot provides a set of models for representing Virtual Private Networks (VPNs), including reusable profiles, policies, and tunnel endpoints. These models enable you to define IKE (Phase 1) and IPSec (Phase 2) policy parameters, manage tunnel endpoints, and associate VPNs with tenants, roles, and secrets.

!!! note
    At present, Nautobot's VPN models are designed to represent tunnel-based VPNs. Support for overlay VPNs (MPLS, VXLAN, etc) is planned for future releases.
