# VPN Tunnel Endpoint

Each VPN Tunnel consists of two endpoints, which are typically located at different sites or networks.

![VPN Tunnel Endpoint List View](../../../media/models/vpn_models_vpntunnelendpoint_list_light.png#only-light){ .on-glb }
![VPN Tunnel Endpoint List View](../../../media/models/vpn_models_vpntunnelendpoint_list_dark.png#only-dark){ .on-glb }

Typically, a VPN Tunnel Endpoint is associated with a specific device interface, which serves as the point of connection for the VPN tunnel. Moreover, each endpoint may be linked to a particular IP address, which is used for establishing the VPN connection. Last, for IPSec-Tunnel type VPNs, the endpoint may optionally be associated with a Tunnel Interface, which is used to encrypt and route traffic through the VPN tunnel.

![VPN Tunnel Endpoint Detail View](../../../media/models/vpn_models_vpntunnelendpoint_detail01_light.png#only-light){ .on-glb }
![VPN Tunnel Endpoint Detail View](../../../media/models/vpn_models_vpntunnelendpoint_detail01_dark.png#only-dark){ .on-glb }

Nevertheless, Nautobot users have the flexibility to create VPN Tunnel Endpoints without associating them with a device interface, IP address, or tunnel interface. This allows for greater versatility in defining VPN tunnel endpoints, especially when dealing with terminating equipment which is not owned by the organization. In this case, users can define an endpoint just by manually specifying its terminating FQDN or IP address.

![VPN Tunnel Endpoint Detail View](../../../media/models/vpn_models_vpntunnelendpoint_detail02_light.png#only-light){ .on-glb }
![VPN Tunnel Endpoint Detail View](../../../media/models/vpn_models_vpntunnelendpoint_detail02_dark.png#only-dark){ .on-glb }

An endpoint may also represent a cloud VPN gateway, such as an AWS virtual private gateway or an Azure VPN gateway, by referencing the [cloud service](../cloud/cloudservice.md) that represents the gateway in its `cloud_service` field. A cloud service is mutually exclusive with a device and a source interface, since the gateway is managed by the cloud provider. Such an endpoint must still define a source IP address or a source FQDN, typically the public IP address or the DNS name of the gateway.

The name of an endpoint is generated automatically. For an endpoint attached to a cloud service, the name is the name of the cloud service, followed by the source IP address or the source FQDN in parentheses, for example `vpngw-hub (203.0.113.10/32)`.

+++ 3.3.0
    The optional `cloud_service` field has been added. The name of an endpoint attached to a cloud service includes the name of the cloud service.

In multiple firewall implementations, users may need to define the encryption domain for a VPN Tunnel (also known as the "interesting traffic" or "local/remote networks"). This is typically done by specifying one or more prefixes that represent the local and remote networks that will be routed through the VPN tunnel. In Nautobot, users can define prefixes "protected" by the VPN Tunnel Endpoint in two ways:

- by explicitly selecting existing Prefix objects or
- by defining a Prefix Dynamic Group that matches the desired prefixes.

This allows for flexible and dynamic management of the networks associated with each VPN Tunnel Endpoint.

Additionally, contextual information about VPN Tunnel Endpoints may be found in the following components:

- Under Device, in the **VPN Endpoints** tab
- Under Interface, as a **VPN Endpoints** side panel
- Under Prefix, as a **VPN Endpoints** side panel
- Under Cloud Service, as a **VPN Tunnel Endpoints** panel, when the cloud service has any
