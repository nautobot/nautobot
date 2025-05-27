# VPN Tunnel

The VPNTunnel model for nautobot_vpn_models provides the following fields:
- `vpn_profile`: VPN Profile
- `vpn`: FK,UK VPN
- `name`: Name
- `description`: Description
- `tunnel_id`: Tunnel ID
- `encapsulation`: IPsec - Transport, IPsec - Tunnel, IP-in-IP, GRE, WireGuard, L2TP, PPTP, OpenVPN, EoIP
- `tenant`: Tenant
- `role`: Role
