# VPN Tunnel

A VPN Tunnel represents a secure communication channel established between two endpoints, usually over a public or untrusted network, such as the internet. In Nautobot, a VPN Tunnel is effectively defined by its two terminating endpoints, and is uniquely identified by its name. When creating a VPN Tunnel, users must also specify its type (encapsulation method), its status, and optionally the VPN it's associated with.

![VPN Tunnel Detail View](../../../media/models/vpn_models_vpntunnel_detail_light.png#only-light){ .on-glb }
![VPN Tunnel Detail View](../../../media/models/vpn_models_vpntunnel_detail_dark.png#only-dark){ .on-glb }

The following encapsulation types are currently supported:

- GRE
- IPSec (transport or tunnel mode)
- IP-in-IP
- L2TP
- OpenVPN
- PPTP
- WireGuard
