# Secrets

+++ 1.2.0

For security reasons, Nautobot generally does not store sensitive secrets (device access credentials, systems-integration API tokens, etc.) in its own database. There are other approaches and systems better suited to this purpose, ranging from simple solutions such as process-specific environment variables or restricted-access files on disk, all the way through to dedicated systems such as Hashicorp Vault or AWS Secrets Manager.

However, any number of Nautobot features (including, but not limited to, device access via NAPALM, Git repository access, custom Jobs, and various plugins seeking to integrate with third-party systems) do need the ability to retrieve and make use of such secrets. Towards that end, Nautobot provides a `Secret` database model. This model does **not** store the secret value itself, but instead defines **how** Nautobot can retrieve the secret value as and when it is needed. By using this model as an abstraction of the underlying secrets storage implementation, this makes it possible for any Nautobot feature to make use of secret values without needing to know or care where or how the secret is actually stored.

Secrets can be grouped and assigned a specific purpose as members of a Secrets Group, which can then be attached to a Git repository, device, or other data model as needed for a given purpose.

## Secrets Providers

Each Secret is associated with a secrets provider (not to be confused with a circuit provider), which provides the functionality needed to retrieve a specific value from a particular source of secrets. Each secrets provider also defines the set of parameters that a given Secret must specify in order to retrieve a secret value from this provider. Nautobot includes the following built-in secrets providers:

- *Environment Variable* - for retrieving a secret value defined in an environment variable; Secrets using this provider must specify the `variable` name to retrieve.
- *Text File* - for retrieving a secret value stored in a text file; Secrets using this provider must specify the absolute `path` of the file to retrieve.

+/- 1.4.3
    When using the Text File secrets provider, any leading and trailing whitespace or newlines will be stripped.

When defining a new Secret, you will need to select the desired secrets provider and then fill in the specific parameters required by that provider in order to have a completely specified, usable Secret record.

!!! tip
    Nautobot plugins can also implement and register additional secrets providers as desired to support other sources such as Hashicorp Vault or AWS Secrets Manager.

## Templated Secret Parameters

In some cases you may have a collection of closely related secrets values that all follow a similar retrieval pattern. For example you might have a directory of text files each containing the unique password for a specific device, or have defined a set of environment variables providing authentication tokens for each different Git repository. In this case, to reduce the need for repeated data entry, Nautobot provides an option to use Jinja2 templates to dynamically alter the provider parameters of a given Secret based on the requesting object. The relevant object is passed to Jinja2 as `obj`. Thus, for example:

- A "Device Password" secret could use the *Text File* provider and specify the file `path` as `"/opt/nautobot/device_passwords/{{ obj.site.slug }}/{{ obj.name }}.txt"`, so that a device `csr1` at site `nyc` would be able to retrieve its password value from `/opt/nautobot/device_passwords/nyc/csr1.txt`.
- A "Git Token" secret could use the *Environment Variable* provider and specify the `variable` name as `"GIT_TOKEN_{{ obj.slug | replace('-', '_') | upper }}"`, so that a Git repository `golden-config` would be able to retrieve its token value from `$GIT_TOKEN_GOLDEN_CONFIG`.
