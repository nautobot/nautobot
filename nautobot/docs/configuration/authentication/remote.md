# Remote User Authentication

Nautobot can be configured to support remote user authentication by inferring users from an HTTP header set by an authenticating reverse proxy (e.g. NGINX).

This document describes how to make use of an external authentication source (where the Web server sets the `REMOTE_USER` environment variable). This type of authentication solution is typically seen on intranet sites, with single sign-on solutions.

User authentication will still fall back to built-in Django users in the event of a failure in remote authentication.

## Installation

Enable the remote user authentication backend by adding the following to your `nautobot_config.py`:

!!! note
    It is critical that you include the `ObjectPermissionsBackend` provided by
    Nautobot after the `RemoteUserBackend` so that object-level permissions features can work properly.

```python
AUTHENTICATION_BACKENDS = [
    'nautobot.core.authentication.RemoteUserBackend',
    'nautobot.core.authentication.ObjectPermissionBackend',
]
```

## Configuration

The following configuration variables describe the default values and as long as `RemoteUserBackend` has been installed as described above, no changes are required.

If you do require customizing any of these settings, they must be set in your `nautobot_config.py`.

### REMOTE_AUTH_AUTO_CREATE_USER

Default: `False`

If set to `True`, local accounts will be automatically created for users authenticated via a remote service.

---

### REMOTE_AUTH_HEADER

Default: `'HTTP_REMOTE_USER'`

When remote user authentication is in use, this is the name of the HTTP header which informs Nautobot of the currently authenticated user. For example, to use the request header `X-Remote-User` it needs to be set to `HTTP_X_REMOTE_USER`.

---

Be sure to configure [`EXTERNAL_AUTH_DEFAULT_GROUPS`](../../configuration/optional-settings.md#external_auth_default_groups) and [`EXTERNAL_AUTH_DEFAULT_PERMISSIONS`](../../configuration/optional-settings.md#external_auth_default_permissions) next.
