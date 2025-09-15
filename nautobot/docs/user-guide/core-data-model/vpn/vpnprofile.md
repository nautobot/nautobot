# VPN Profile

A VPN Profile is a reusable template that combines the parameters for IKE (Phase 1) and IPSec (Phase 2) policies into a single entity which can be applied to multiple VPN tunnels. To further facilitate organization and management, a VPN Profile can be associated with multiple Phase 1 and Phase 2 policies, ordered by defined weights to determine their priority. VPN Profiles can also be associated with Secrets, ensuring that sensitive information such as pre-shared keys or certificates are managed securely.

Nautobot users can create and manage VPN Profiles to standardize the configuration of VPN tunnels across their network infrastructure. Additionally, several VPN profiles are available by default in Nautobot to facilitate quick setup.

| Name                         | VPN Phase 1 Policy          | VPN Phase 2 Policy           | Enable keepalive | Keepalive interval | Keepalive retries | Enable NAT traversal |
|------------------------------|-----------------------------|------------------------------|------------------|--------------------|-------------------|----------------------|
| High-Security Profile        | High-Security Policy        | High-Security Policy         | True             | 15                 | 4                 | False                |
| Standard Profile             | Standard Policy             | Standard Policy              | True             | 10                 | 3                 | False                |
| Performance-Oriented Profile | Performance-Oriented Policy | Performance-Oriented Policy  | True             | 5                  | 2                 | False                |
| Remote Access Profile        | Remote Access Policy        | Remote Access Policy         | True             | 30                 | 5                 | False                |
