# External Integrations

+++ 2.1.0

The external integration feature provides a centralized store for data such as URLs and credentials that are used to access systems external to Nautobot. This information can then be used by jobs or apps to perform actions such as creating DNS records or updating configuration management tickets.

The external integration model includes the following fields:

- **Name** - The name of the external integration. This must be unique.
- **Remote URL** - The URL used to access the external system. (ex: `https://service.example.com/api/v1/`)
- **HTTP Method** - The type of HTTP request to send. Options include `GET`, `POST`, `PUT`, `PATCH`, and `DELETE`.
- **Headers** - The headers to include with the request (optional). Include the headers in valid JSON format `{"header" : "value"}`. Jinja2 templating is supported for this field (see below).
- **Secrets Group** - Optional secrets group used to store credentials for the external system.
- **SSL Verification** - Whether or not to verify the SSL certificate of the external system.
- **CA File Path** - The file path to a particular certificate authority (CA) file to use when validating the receiver's SSL certificate (optional).
- **Timeout** - The number of seconds to wait for a response from the external system before timing out.
- **Extra Config** - Additional configuration related to the external system. This field is optional and can be used to store any additional parameters required to access the external system. This field is stored as a JSON object.

## Jinja2 Template Support

[Jinja2 templating](https://jinja.palletsprojects.com/) is supported for the `remote_url`, `headers` and `extra_config` fields. This enables the user to render URLs and credentials as well as their request headers and extra configurations required to interact with systems external to Nautobot. Code consuming this model can use the `ExternalIntegration.render_remote_url()`, `.render_headers()`, and `.render_extra_config()` APIs as appropriate.
