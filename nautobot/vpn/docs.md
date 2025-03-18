# TODO INIT Move into individual md files for each models.











# VPN Profile

The VPNProfile model for nautobot_vpn_models provides the following fields:
- `vpn_phase1_policy`: Phase 1 Policy
- `vpn_phase2_policy`: Phase 2 Policy
- `name`: Name
- `description`: Description
- `keepalive_enabled`: Keepalive enabled
- `keepalive_interval`: Keepalive interval
- `keepalive_retries`: Keepalive retries
- `nat_traversal`: NAT traversal
- `extra_options`: Extra options
- `secrets_group`: 
- `role`: Role



# VPN Phase 1 Policy

The VPNPhase1Policy model for nautobot_vpn_models provides the following fields:
- `name`: Name
- `description`: Description
- `ike_version`: IKEv1, IKEv2
- `aggressive_mode`: Use aggressive mode
- `encryption_algorithm`: AES-256-GCM, AES-256-CBC, AES-192-GCM, AES-192-CBC, AES-128-GCM, AES-128-CBC, 3DES, DES
- `integrity_algorithm`: SHA512, SHA384, SHA256, SHA1, MD5
- `dh_group`: Diffie-Hellman group
- `lifetime_seconds`: Lifetime in seconds
- `lifetime_kb`: Lifetime in kiolbytes
- `authentication_method`: PSK, RSA, ECDSA, Certificate



# VPN Phase 2 Policy

The VPNPhase2Policy model for nautobot_vpn_models provides the following fields:
- `name`: Name
- `description`: Description
- `encryption_algorithm`: AES-256-GCM, AES-256-CBC, AES-192-GCM, AES-192-CBC, AES-128-GCM, AES-128-CBC, 3DES, DES
- `integrity_algorithm`: SHA512, SHA384, SHA256, SHA1, MD5
- `pfs_group`: Perfect Forward Secrecy group
- `lifetime`: Lifetime in seconds



# VPN

The VPN model for nautobot_vpn_models provides the following fields:
- `vpn_profile`: VPN Profile
- `name`: Name
- `description`: Description
- `vpn_id`: VPN ID
- `tenant`: Tenant
- `role`: Role
- `contact_associations`: Contact Associations



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
- `contact_associations`: Contact Associations



# VPN Tunnel Endpoint

The VPNTunnelEndpoint model for nautobot_vpn_models provides the following fields:
- `vpn_profile`: VPN Profile
- `vpn_tunnel`: FK,UK VPN Tunnel
- `source_ipaddress`: FK,UK Source IP Address
- `source_interface`: Source Interface
- `destination_ipaddress`: Destination IP Address
- `destination_fqdn`: Destination FQDN
- `tunnel_interface`: Tunnel Interface
- `protected_prefixes_dg`: Protected Prefixes in Dynamic Groups
- `protected_prefixes`: Protected Prefixes
- `role`: Role
- `contact_associations`: Contact Associations


