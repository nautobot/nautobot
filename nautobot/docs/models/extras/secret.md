# Secrets

For security reasons, Nautobot does not store sensitive secrets (device access credentials, systems-integration API tokens, etc.) in its own database. There are other approaches and systems better suited to this purpose, ranging from simple solutions such as process-specific environment variables or restricted-access files on disk all the way through to dedicated systems such as Hashicorp Vault or AWS Secrets Manager.

However, any number of Nautobot features (including, but not limited to, device access via NAPALM, Git repository access, custom Jobs, and various plugins seeking to integrate with third-party systems) do need the ability to retrieve and make use of such secrets. Towards that end, Nautobot provides a `Secret` database model. This model does **not** store the secret value itself, but instead defines **how** Nautobot can retrieve the secret value as needed. By using this model as an abstraction of the underlying secrets storage implementation, this makes it possible for any Nautobot feature to make use of secret values without needing to know or care where or how the secret is actually stored.

## Secrets Providers

Each Secret is associated with a secrets provider (not to be confused with a circuit provider), which provides the functionality needed to retrieve a value from a particular source of secrets. Nautobot includes the following built-in secrets providers:

- `EnvironmentVariableSecretProvider` - for retrieving a secret value defined in an environment variable
- `TextFileSecretProvider` - for retrieving a secret value stored in a text file

Nautobot plugins can also [implement and provide](../../plugins/development.md#implementing-secrets-providers) additional secrets providers as desired to support other sources such as Hashicorp Vault or AWS Secrets Manager.

## Secret Parameters

Each secrets provider defines a set of provider-specific parameters that a Secret must specify in order to successfully retrieve the specific secret value desired. For example:

- `EnvironmentVariableSecretProvider` requires a `variable` parameter, specifying the name of the variable to retrieve
- `TextFileSecretProvider` requires a `path` parameter, specifying the filesystem path to load the secret value from.

When defining a new Secret, you will need to select the desired secrets provider and then fill in the specific parameters required by that provider in order to have a completely specified, usable Secret record.
