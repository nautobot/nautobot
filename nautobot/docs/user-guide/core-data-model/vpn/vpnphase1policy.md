# VPN Phase 1 Policy

A VPN Phase 1 Policy defines IKE Phase 1 (ISAKMP) policy parameters. These parameters include the IKE version, encryption and integrity algorithms, Diffie-Hellman groups, lifetime settings, and authentication methods. Phase 1 policies are reusable and can be associated with multiple VPN profiles.


Nautobot users can create and manage VPN Phase 1 Policies to standardize the configuration of VPN tunnels across their network infrastructure. Additionally, several Phase 1 policies are available by default in Nautobot to facilitate quick setup.

| Name.                       | IKE Version | Encryption Algorithm | Integrity Algorithm | DH Group | Lifetime (seconds) |
|-----------------------------|-------------|----------------------|---------------------|----------|--------------------|
| High-Security Policy        | IKEv2       | AES-256-GCM          | SHA512              | 21       | 86400              |
| Standard Policy             | IKEv2       | AES-256-CBC          | SHA256              | 14       | 86400              |
| Performance-Oriented Policy | IKEv2       | AES-128-CBC          | SHA256              | 5        | 86400              |
| Remote Access Policy        | IKEv2       | AES-256-CBC          | SHA256              | 19       | 28800              |
