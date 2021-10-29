# Secrets

For security reasons, Nautobot generally does not store sensitive secrets (device access credentials, systems-integration API tokens, etc.) in its own database. There are other approaches and systems better suited to this purpose, ranging from simple solutions such as process-specific environment variables or restricted-access files on disk, all the way through to dedicated systems such as Hashicorp Vault or AWS Secrets Manager.

However, any number of Nautobot features (including, but not limited to, device access via NAPALM, Git repository access, custom Jobs, and various plugins seeking to integrate with third-party systems) do need the ability to retrieve and make use of such secrets. Towards that end, Nautobot provides a `Secret` database model. This model does **not** store the secret value itself, but instead defines **how** Nautobot can retrieve the secret value as and when it is needed. By using this model as an abstraction of the underlying secrets storage implementation, this makes it possible for any Nautobot feature to make use of secret values without needing to know or care where or how the secret is actually stored.

Secrets can be grouped and assigned a specific purpose as members of a [secrets group](./secretsgroup.md), which can then be attached to a Git repository, device, or other data model as needed for a given purpose.

## Secrets Providers

Each Secret is associated with a secrets provider (not to be confused with a circuit provider), which provides the functionality needed to retrieve a specific value from a particular source of secrets. Each secrets provider also defines the set of parameters that a given Secret must specify in order to retrieve a secret value from this provider. Nautobot includes the following built-in secrets providers:

- `EnvironmentVariableSecretsProvider` - for retrieving a secret value defined in an environment variable; Secrets using this provider must specify the `variable` name to retrieve.
- `TextFileSecretsProvider` - for retrieving a secret value stored in a text file; Secrets using this provider must specify the absolute `path` of the file to retrieve.

When defining a new Secret, you will need to select the desired secrets provider and then fill in the specific parameters required by that provider in order to have a completely specified, usable Secret record.

!!! tip
    Nautobot plugins can also [implement and provide](../../plugins/development.md#implementing-secrets-providers) additional secrets providers as desired to support other sources such as Hashicorp Vault or AWS Secrets Manager.

## Secrets and Security

Secrets are of course closely linked to security, and as such they pose a number of unique concerns that are worth discussing.

### Leakage of Secret Values

By design, the UI, REST API, and GraphQL do **not** provide access to retrieve or report the actual value of any given Secret, as these values are only meant for use *within* Nautobot itself.

!!! tip
    If you need to use a secret value for some other purpose (such as to manually log into a device, or query an authenticated REST API endpoint yourself), you should be retrieving the value directly from the appropriate secrets provider rather than trying to relay it through Nautobot.

However, code is power, and with power comes responsibility.

!!! warning
    Any user or process that has the ability to execute code within Nautobot has the **potential** to access the value of any Secret, and a user or process that has the ability to execute *arbitrary* code absolutely **can** access Secrets.

What does this mean in practice?

- Any [plugin](../../plugins/index.md) can potentially access your Secrets, including displaying their values onscreen or even forwarding them to an external system, so only install plugins that you trust.
- Any [Job](../../additional-features/jobs.md) can potentially access your Secrets, and can trivially log a Secret value to its JobResult, where it may be visible to users, so only install Jobs that you trust, carefully limit which users are able to execute jobs and view job results, and be aware of the potential for privilege escalation resulting from careless or malicious logging.
- Any [Git repository](./gitrepository.md) can add new Jobs to your system, so be careful about which users you grant the ability to create/edit `GitRepository` records.
- Any user with access to `nautobot-server nbshell` can execute arbitrary code, including accessing Secrets, and will be able to bypass any Nautobot permissions restrictions as well.

### Using Object Permissions with Secrets

!!! tip
    In practice you will likely want to carefully restrict which users are allowed to define and edit Secrets, and may want to use [object permissions](../../administration/permissions.md) to further restrict which specific Secrets they are allowed to make use of.

The two default Secrets providers potentially allow a user to define and make use of a Secret corresponding to any environment variable in the Nautobot execution context and/or any file readable by the `nautobot` user. For many users and use cases, you will not want to grant this much power to define and access arbitrary secrets; fortunately Nautobot's built-in permissions model is granular enough to allow for more specifically tailored access grants.

For example, to restrict a specific user to only be able to work with Secrets that use the `environment-variable` Secrets provider, and specifically only to access those environment variables whose names begin with `NAPALM_`, you could define a Permission with a specific constraint like:

```json
{
    "provider": "environment-variable",
    "parameters__variable__startswith": "NAPALM_"
}
```

Or for a Permission to work with Secrets that use `text-file`, but only files located in `/opt/nautobot/secrets/`, you could use the following constraint:

```json
{
    "provider": "text-file",
    "parameters__path__startswith": "/opt/nautobot/secrets/"
}
```

## Using Secrets in Code

Accessing a Secret's value from code is as simple as accessing its `value` property:

```python
>>> secret = Secret.objects.get(slug="napalm_username")
>>> secret.value
'user'
```

In the case where a secret's value cannot be retrieved successfully, Nautobot will raise a `SecretError` or one of its subclasses:

```python
>>> from nautobot.extras.secrets.exceptions import SecretError
>>> try:
...     Secret.objects.get(slug="napalm_password").value
... except SecretError as exc:
...     print(exc)
...
SecretValueNotFoundError: Secret "NAPALM Password" (provider "EnvironmentVariableSecretsProvider"): Undefined environment variable "NAPALM_PASSWORD"!
```
