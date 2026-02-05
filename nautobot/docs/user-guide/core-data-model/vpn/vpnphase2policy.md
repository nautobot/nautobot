# VPN Phase 2 Policy

A VPN Phase 2 Policy defines IPSec Phase 2 policy parameters. These parameters include the encapsulation mode, encryption and integrity algorithms, PFS (Perfect Forward Secrecy) groups, and lifetime settings. Phase 2 policies are reusable and can be associated with multiple VPN profiles.

Nautobot users can create and manage VPN Phase 2 Policies to standardize the configuration of VPN tunnels across their network infrastructure. Additionally, several Phase 2 policies are available by default in Nautobot to facilitate quick setup.

| Name                        | Encryption Algorithm | Integrity Algorithm | PFS Group | Lifetime (seconds) |
|-----------------------------|--------------------|----------------------|------------|--------------------|
| High-Security Policy        | AES-256-GCM        | SHA512               | 21         | 1800               |
| Standard Policy             | AES-256-CBC        | SHA256               | 14         | 3600               |
| Performance-Oriented Policy | AES-128-CBC        | SHA256               | -          | 3600               |
| Remote Access Policy        | AES-256-CBC        | SHA256               | 19         | 1800               |
