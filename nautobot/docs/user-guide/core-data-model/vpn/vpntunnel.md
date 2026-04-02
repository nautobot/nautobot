# VPN Tunnel

A VPN Tunnel represents a secure communication channel established between two endpoints, usually over a public or untrusted network, such as the internet. In Nautobot, a VPN Tunnel is effectively defined by its two terminating endpoints, and is uniquely identified by its name. When creating a VPN Tunnel, users must also specify its type (encapsulation method), its status, and optionally the VPN it's associated with.

For convenience, users can also assign a VPN Profile to the tunnel which will allow them to easily apply a predefined set of parameters for IKE and IPSec policies as well as keepalive settings. However, it remains the user's responsibility to decide how to use and consume these features in their configuration templates. We consider introducing an inheritance mechanism in a later version that will make VPN Profiles even easier to use.

+++ 3.1.0
    In addition to VPN Profiles, a Secrets Group may be assigned directly to a VPN Tunnel to manage sensitive information. This approach enables administrators to apply a common, secret-free VPN Profile across multiple VPN Tunnels, even when those tunnels require distinct credentials. Furthermore, it facilitates the independent management of secrets and VPN Profiles, offering enhanced flexibility for various deployment scenarios.

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
