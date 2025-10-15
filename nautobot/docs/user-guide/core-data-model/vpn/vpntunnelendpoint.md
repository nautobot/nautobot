# VPN Tunnel Endpoint

Each VPN Tunnel consists of two endpoints, which are typically located at different sites or networks.

![VPN Tunnel Endpoint List View](../../../media/models/vpn_models_vpntunnelendpoint_list_light.png#only-light)
![VPN Tunnel Endpoint List View](../../../media/models/vpn_models_vpntunnelendpoint_list_dark.png#only-dark)

Typically, a VPN Tunnel Endpoint is associated with a specific device interface, which serves as the point of connection for the VPN tunnel. Moreover, each endpoint may be linked to a particular IP address, which is used for establishing the VPN connection. Last, for IPSec-Tunnel type VPNs, the endpoint may optionally be associated with a Tunnel Interface, which is used to encrypt and route traffic through the VPN tunnel.

![VPN Tunnel Endpoint Detail View](../../../media/models/vpn_models_vpntunnelendpoint_detail01_light.png#only-light)
![VPN Tunnel Endpoint Detail View](../../../media/models/vpn_models_vpntunnelendpoint_detail01_dark.png#only-dark)

Nevertheless, Nautobot users have the flexibility to create VPN Tunnel Endpoints without associating them with a device interface, IP address, or tunnel interface. This allows for greater versatility in defining VPN tunnel endpoints, especially when dealing with terminating equipment which is not owned by the organization. In this case, users can define an endpoint just by manually specifying its terminating FQDN or IP address.

![VPN Tunnel Endpoint Detail View](../../../media/models/vpn_models_vpntunnelendpoint_detail02_light.png#only-light)
![VPN Tunnel Endpoint Detail View](../../../media/models/vpn_models_vpntunnelendpoint_detail02_dark.png#only-dark)

In multiple firewall implementations, users may need to define the encryption domain for a VPN Tunnel (also known as the "interesting traffic" or "local/remote networks"). This is typically done by specifying one or more prefixes that represent the local and remote networks that will be routed through the VPN tunnel. In Nautobot, users can define prefixes "protected" by the VPN Tunnel Endpoint in two ways: either by explicitly selecting existing Prefix objects or by defining a Prefix Dynamic Group that matches the desired prefixes. This allows for flexible and dynamic management of the networks associated with each VPN Tunnel Endpoint.
