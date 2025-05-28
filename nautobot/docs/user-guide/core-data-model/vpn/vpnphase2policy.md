# VPN Phase 2 Policy

The VPNPhase2Policy model for VPNs provides the following fields:

- `name`: Name
- `description`: Description
- `encryption_algorithm`: AES-256-GCM, AES-256-CBC, AES-192-GCM, AES-192-CBC, AES-128-GCM, AES-128-CBC, 3DES, DES
- `integrity_algorithm`: SHA512, SHA384, SHA256, SHA1, MD5
- `pfs_group`: Perfect Forward Secrecy group
- `lifetime`: Lifetime in seconds
