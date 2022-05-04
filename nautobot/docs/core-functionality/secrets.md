# Secrets

{%
    include-markdown "../models/extras/secret.md"
    heading-offset=1
%}

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

- Any [plugin](../plugins/index.md) can potentially access your Secrets, including displaying their values onscreen or even forwarding them to an external system, so only install plugins that you trust.
- Any [Job](../additional-features/jobs.md) can potentially access your Secrets, and can trivially log a Secret value to its JobResult, where it may be visible to users, so only install Jobs that you trust, carefully limit which users are able to execute jobs and view job results, and be aware of the potential for privilege escalation resulting from careless or malicious logging.
- Any [Git repository](../models/extras/gitrepository.md) can add new Jobs to your system, so be careful about which users you grant the ability to create/edit `GitRepository` records.
- Any user with access to [`nautobot-server nbshell`](../administration/nautobot-shell.md) can execute arbitrary code, including accessing Secrets, and will be able to bypass any Nautobot permissions restrictions as well.
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

{%
    include-markdown "../models/extras/secretsgroup.md"
    heading-offset=1
%}

## Accessing Secrets in Code

Accessing a Secret's value from code is as simple as calling its `get_value()` method. Providing an `obj` parameter for context is recommended so as to allow for proper handling of templated secret parameters:

```python
>>> secret = Secret.objects.get(slug="napalm-username")
>>> secret.get_value()
'user'
>>> secret = Secret.objects.get(slug="napalm-password")
>>> secret.get_value(obj=device1)
'secret-device1-password'
```

In the case where a secret's value cannot be retrieved successfully, Nautobot will raise a `SecretError` or one of its subclasses:

```python
>>> from nautobot.extras.secrets.exceptions import SecretError
>>> try:
...     Secret.objects.get(slug="napalm-secret").get_value()
... except SecretError as exc:
...     print(exc)
...
SecretValueNotFoundError: Secret "NAPALM Secret" (provider "EnvironmentVariableSecretsProvider"): Undefined environment variable "NAPALM_SECRET"!
```

In many cases, rather than accessing a specific Secret directly, you will be working with a Secrets Group instead. To retrieve the value of a specific secret within a group, use the group's `get_secret_value()` method, again with the option of providing an `obj` for template context:

```python
>>> secrets_group = SecretsGroup.objects.get(slug="netconf-credentials")
>>> from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
>>> secrets_group.get_secret_value(
...     access_type=SecretsGroupAccessTypeChoices.TYPE_NETCONF,
...     secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
...     obj=device1,
... )
"user-device1"
```
