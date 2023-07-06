# Secrets

+++ 1.2.0

For security reasons, Nautobot generally does not store sensitive secrets (device access credentials, systems-integration API tokens, etc.) in its own database. There are other approaches and systems better suited to this purpose, ranging from simple solutions such as process-specific environment variables or restricted-access files on disk, all the way through to dedicated systems such as Hashicorp Vault or AWS Secrets Manager.

However, any number of Nautobot features (including, but not limited to, device access via NAPALM, Git repository access, custom Jobs, and various plugins seeking to integrate with third-party systems) do need the ability to retrieve and make use of such secrets. Towards that end, Nautobot provides a `Secret` database model. This model does **not** store the secret value itself, but instead defines **how** Nautobot can retrieve the secret value as and when it is needed. By using this model as an abstraction of the underlying secrets storage implementation, this makes it possible for any Nautobot feature to make use of secret values without needing to know or care where or how the secret is actually stored.

Secrets can be grouped and assigned a specific purpose as members of a Secrets Group, which can then be attached to a Git repository, device, or other data model as needed for a given purpose.

## Secrets Groups

+++ 1.2.0

A Secrets Group provides a way to collect and assign a purpose to one or more Secrets. The Secrets Group can then be attached to any object that needs to reference and make use of these Secrets, such as a Git repository needing a username/token to authenticate to a private GitHub repository, or a device using a group of Secrets to drive its NAPALM integration.

When creating or editing a Secrets Group, you can assign any number of defined Secrets to this group, assigning each secret an *access type* and a *secret type* that are unique within the context of this group. Some examples of how a Secrets Group might be populated for use by a given feature:

| Feature                   | Access Type | Secrets Type(s)                                     |
|---------------------------|-------------|-----------------------------------------------------|
| Git private repository    | `HTTP(S)`   | `Token`, possibly also `Username`                   |
| Device NAPALM integration | `Generic`   | `Username`, `Password`, possibly an enable `Secret` |

A Secrets Group is not limited to containing secrets of a single *access type* either - for example, a plugin that supports both NETCONF and gNMI protocols to interact with a device could be able to make use of a Secrets Group containing distinct secrets for each protocol.

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

- A "Device Password" secret could use the *Text File* provider and specify the file `path` as `"/opt/nautobot/device_passwords/{{ obj.location.name }}/{{ obj.name }}.txt"`, so that a device `csr1` at location `NYC` would be able to retrieve its password value from `/opt/nautobot/device_passwords/NYC/csr1.txt`.
- A "Git Token" secret could use the *Environment Variable* provider and specify the `variable` name as `"GIT_TOKEN_{{ obj.slug | upper }}"`, so that a Git repository `golden_config` would be able to retrieve its token value from `$GIT_TOKEN_GOLDEN_CONFIG`.

!!! note
    To access custom fields of an object within a template, use the `cf` attribute. For example, `{{ obj.cf.color }}` will return the value (if any) for the custom field with a key of `color` on `obj`.

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

- Any [plugin](../../apps/index.md) can potentially access your Secrets, including displaying their values onscreen or even forwarding them to an external system, so only install plugins that you trust.
- Any [Job](./jobs/index.md) can potentially access your Secrets, and can trivially log a Secret value to its JobResult, where it may be visible to users, so only install Jobs that you trust, carefully limit which users are able to execute jobs and view job results, and be aware of the potential for privilege escalation resulting from careless or malicious logging.
- Any [Git repository](./gitrepository.md) can add new Jobs to your system, so be careful about which users you grant the ability to create/edit `GitRepository` records.
- Any user with access to [`nautobot-server nbshell`](../administration/tools/nautobot-shell.md) can execute arbitrary code, including accessing Secrets, and will be able to bypass any Nautobot permissions restrictions as well.
- Any user with access to modify Secrets can take advantage of a leak of one Secret's information through any of the above vectors to additionally leak other secret values (except as restricted with [object permissions](#using-object-permissions-with-secrets), see below). For example, if a Job erroneously logs a username obtained from a Secret as a part of its output, a user could modify the corresponding Secret definition to make the Job log any other secret value they have access to.

### Using Object Permissions with Secrets

!!! tip
    In practice you will likely want to carefully restrict which users are allowed to define and edit Secrets, and may want to use object permissions to further restrict which specific Secrets they are allowed to utilize.

The two default Secrets providers potentially allow a user to define and use a Secret corresponding to any environment variable in the Nautobot execution context and/or any file readable by the `nautobot` user. For many users and use cases, you will not want to grant this much power to define and access arbitrary secrets; fortunately Nautobot's built-in permissions model is granular enough to allow for more specifically tailored access grants.

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

## Accessing Secrets in Code

Accessing a Secret's value from code is as simple as calling its `get_value()` method. Providing an `obj` parameter for context is recommended so as to allow for proper handling of templated secret parameters:

```python
>>> secret = Secret.objects.get(name="NAPALM Username")
>>> secret.get_value()
'user'
>>> secret = Secret.objects.get(name="NAPALM Password")
>>> secret.get_value(obj=device1)
'secret-device1-password'
```

In the case where a secret's value cannot be retrieved successfully, Nautobot will raise a `SecretError` or one of its subclasses:

```python
>>> from nautobot.extras.secrets.exceptions import SecretError
>>> try:
...     Secret.objects.get(name="NAPALM Secret").get_value()
... except SecretError as exc:
...     print(exc)
...
SecretValueNotFoundError: Secret "NAPALM Secret" (provider "EnvironmentVariableSecretsProvider"): Undefined environment variable "NAPALM_SECRET"!
```

In many cases, rather than accessing a specific Secret directly, you will be working with a Secrets Group instead. To retrieve the value of a specific secret within a group, use the group's `get_secret_value()` method, again with the option of providing an `obj` for template context:

```python
>>> secrets_group = SecretsGroup.objects.get(name="NETCONF Credentials")
>>> from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
>>> secrets_group.get_secret_value(
...     access_type=SecretsGroupAccessTypeChoices.TYPE_NETCONF,
...     secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
...     obj=device1,
... )
"user-device1"
```
