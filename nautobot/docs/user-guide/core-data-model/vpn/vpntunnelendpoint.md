# VPN Tunnel Endpoint

The VPNTunnelEndpoint model for nautobot_vpn_models provides the following fields:
- `vpn_profile`: VPN Profile
- `vpn_tunnel`: FK,UK VPN Tunnel
- `source_ipaddress`: FK,UK Source IP Address
- `source_interface`: Source Interface
- `source_ipaddress`: Destination IP Address
- `source_fqdn`: Destination FQDN
- `tunnel_interface`: Tunnel Interface
- `protected_prefixes_dg`: Protected Prefixes in Dynamic Groups
- `protected_prefixes`: Protected Prefixes
- `role`: Role
