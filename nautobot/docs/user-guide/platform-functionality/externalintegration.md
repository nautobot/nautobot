# External Integrations

+++ 2.1.0

The external integration feature provides a centralized store for data such as URLs and credentials that are used to access systems external to Nautobot. This information can then be used by jobs or apps to perform actions such as creating DNS records or updating configuration management tickets.

The external integration model includes the following fields:

- **Name** - The name of the external integration. This must be unique.
- **Remote URL** - The URL used to access the external system. (ex: `https://service.example.com/api/v1/`)
- **Secrets Group** - Optional secrets group used to store credentials for the external system.
- **SSL Verification** - Whether or not to verify the SSL certificate of the external system.
- **Timeout** - The number of seconds to wait for a response from the external system before timing out.
- **Extra Config** - Additional configuration related to the external system. This field is optional and can be used to store any additional parameters required to access the external system. This field is stored as a JSON object.
