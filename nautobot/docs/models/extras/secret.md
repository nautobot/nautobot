# Secrets

For security reasons, Nautobot does not store sensitive secrets (device access credentials, systems-integration API tokens, etc.) in its own database. There are other approaches and systems better suited to this purpose, ranging from simple solutions such as process-specific environment variables or restricted-access files on disk all the way through to dedicated systems such as Hashicorp Vault or AWS Secrets Manager.

However, any number of Nautobot features (including, but not limited to, device access via NAPALM, Git repository access, custom Jobs, and various plugins seeking to integrate with third-party systems) do need the ability to retrieve and make use of such secrets. Towards that end, Nautobot provides a `Secret` database model. This model does **not** store the secret value itself, but instead defines **how** Nautobot can retrieve the secret value as needed. By using this model as an abstraction of the underlying secrets storage implementation, this makes it possible for any Nautobot feature to make use of secret values without needing to know or care where or how the secret is actually stored.

## Secrets Providers

Each Secret is associated with a secrets provider (not to be confused with a circuit provider), which provides the functionality needed to retrieve a value from a particular source of secrets. Nautobot includes the following built-in secrets providers:

- `EnvironmentVariableSecretsProvider` - for retrieving a secret value defined in an environment variable
- `TextFileSecretsProvider` - for retrieving a secret value stored in a text file

Nautobot plugins can also [implement and provide](../../plugins/development.md#implementing-secrets-providers) additional secrets providers as desired to support other sources such as Hashicorp Vault or AWS Secrets Manager.

## Secret Parameters

Each secrets provider defines a set of provider-specific parameters that a Secret must specify in order to successfully retrieve the specific secret value desired. For example:

- `EnvironmentVariableSecretsProvider` requires a `variable` parameter, specifying the name of the variable to retrieve
- `TextFileSecretsProvider` requires a `path` parameter, specifying the filesystem path to load the secret value from.

When defining a new Secret, you will need to select the desired secrets provider and then fill in the specific parameters required by that provider in order to have a completely specified, usable Secret record.

## Secrets and Security

Secrets are of course closely linked to security, and pose a number of unique concerns that are worth discussing.

### Leakage of Secret Values

By design, the UI, REST API, and GraphQL do *not* provide access to retrieve or report the actual value of any given Secret, as these values are only meant for use *within* Nautobot. If you need to use a secret value for some other purpose, you should be retrieving the value directly from the appropriate provider rather than relaying it through Nautobot.

However, code is power, and with power comes responsibility. Any user or process that has the ability to execute code within Nautobot has the potential to access the value of any Secret, and a user or process that has the ability to execute *arbitrary* code absolutely has the ability to do so. What does this mean in practice?

- Any [plugin](../../plugins/index.md)  can potentially access your defined Secrets, including displaying their values onscreen or even forwarding them to an external system, so only install and run plugins that you trust.
- Any [Job](../../additional-features/jobs.md) can potentially access your Secrets, and can trivially log a Secret value to its JobResult, where it will be visible to users, so only install and execute Jobs that you trust and be aware of the potential for privilege escalation resulting from careless or malicious logging.
- Any [Git repository](./gitrepository.md) can add new Jobs to your system, so be careful about which users you grant the ability to create/edit `GitRepository` records.
- Any user with access to `nautobot-server nbshell` can execute arbitrary code, including accessing Secrets (and of course many other equally destructive or dangerous things as well).

### Using Object Permissions with Secrets

The two default Secrets providers potentially allow a user to define and make use of a Secret corresponding to any environment variable in the Nautobot execution context and/or any file readable by the `nautobot` user. In practice you will likely want to carefully restrict which users are allowed to define and edit Secrets, and may want to use [object permissions](../../administrations/permissions.md) to further restrict which specific Secrets they are allowed to make use of.

For example, to restrict a specific user to only be able to create and edit Secrets that use the `environment-variable` Secrets provider, and specifically only to access those environment variables whose names begin with `NAPALM_`, you could define a Permission with a specific constraint like:

```json
{
    "provider": "environment-variable",
    "parameters__variable__startswith": "NAPALM_"
}
```

Or for a permission to work with Secrets that use `text-file`, but only files located in `/opt/nautobot/secrets/`:

```json
{
    "provider": "text-file",
    "parameters__path__startswith": "/opt/nautobot/secrets/"
}
```
