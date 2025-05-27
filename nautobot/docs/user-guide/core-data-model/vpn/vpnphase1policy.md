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
