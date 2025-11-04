# Certificate Profile

## Overview

The CertificateProfile model is designed to manage SSL/TLS certificates for Load Balancers, ensuring secure encrypted connections between clients and backend services. It serves as a reusable configuration that can be linked to one or more Load Balancers.

The CertificateProfile model provides the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique name to identify the certificate profile. |
| `certificate_type` | choice | No | Indicates use case (e.g., server, client). Valid choices are; "Client", "Server", "mTLS (Mutual TLS)"|
| `certificate_file_path` | string | No | Path to the certificate file. |
| `chain_file_path` | string | No | Path to the certificate chain file. |
| `key_file_path` | string | No | Path to the private key file. |
| `expiration_date` | datetime | No | Certificate expiration date, for tracking purposes. |
| `cipher` | string | No | SSL/TLS cipher string associated with this certificate. |
| `tenant` | ForeignKey to Tenant | No | Optional tenant ownership. |

## Details

The `CertificateProfile` model stores metadata related to SSL/TLS certificates that may be used for secure communication in load balanced environments. These profiles are referenced by `VirtualServer` or `LoadBalancerPoolMember` objects when SSL offload is enabled.

!!! note
    In some vendor systems (e.g., F5), these profiles may be referred to as **SSL Profiles**. In the Load Balancer App, the equivalent data model is `CertificateProfile`.

- This model does not store the actual certificate or key content—only file paths and identification details for integration with external systems or device configurations.
- Certificate Profiles are optional and only used when `ssl_offload` is enabled.
- The fields assume that actual certificate files are stored outside of Nautobot (e.g., on managed devices or external secrets engines).
- Multiple profiles can be applied to the same virtual server or pool member if needed.
- These profiles are often referenced when rendering device-specific configurations, such as Jinja2 templates for F5, A10, or other SSL-terminating devices.
