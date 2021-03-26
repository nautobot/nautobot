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

### REMOTE_AUTH_DEFAULT_GROUPS

Default: `[]` (Empty list)

The list of groups to assign a new user account when created using remote authentication.

---

### REMOTE_AUTH_DEFAULT_PERMISSIONS

Default: `{}` (Empty dictionary)

A mapping of permissions to assign a new user account when created using SSO authentication. Each key in the dictionary will be the permission name specified as `<app_label>.<action>_<model>`, and the value should be set to the permission [constraints](../../administration/permissions.md#constraints), or `None` to allow all objects.

#### Example Permissions

| Permission | Description |
|---|---|
| `{'dcim.view_device': {}}` or `{'dcim.view_device': None}` | Users can view all devices |
| `{'dcim.add_device': {}}` | Users can add devices, see note below |
| `{'dcim.view_device': {"site__name__in":  ["HQ"]}}` | Users can view all devices in the HQ site |

!!! warning
    Permissions can be complicated! Be careful when restricting permissions to also add any required prerequisite permissions.

    For example, when adding Devices the Device Role, Device Type, Site, and Status fields are all required fields in order for the UI to function properly. Users will also need view permissions for those fields or the corresponding field selections in the UI will be unavailable and potentially prevent objects from being able to be created or edited.

The following example gives a user a reasonable amount of access to add devices to a single site (HQ in this case):

```python
{
    'dcim.add_device': {"site__name__in":  ["HQ"]},
    'dcim.view_device': {"site__name__in":  ["HQ"]},
    'dcim.view_devicerole': None,
    'dcim.view_devicetype': None,
    'extras.view_status': None,
    'dcim.view_site': {"name__in":  ["HQ"]},
    'dcim.view_manufacturer': None,
    'dcim.view_region': None,
    'dcim.view_rack': None,
    'dcim.view_rackgroup': None,
    'dcim.view_platform': None,
    'virtualization.view_cluster': None,
    'virtualization.view_clustergroup': None,
    'tenancy.view_tenant': None,
    'tenancy.view_tenantgroup': None,
}
```

Please see [the object permissions page](../../administration/permissions.md) for more information.

---

### REMOTE_AUTH_ENABLED

!!! warning
    This setting is deprecated and will be removed in a future release.

    Toggling this setting to `False` will disable remote user authentication if
    it is installed as specified in this document.

Default: `True`

Set this to `False` to quickly disable this method of authentication. Local authentication will still take effect as a fallback.

---

### REMOTE_AUTH_HEADER

Default: `'HTTP_REMOTE_USER'`

When remote user authentication is in use, this is the name of the HTTP header which informs Nautobot of the currently authenticated user. For example, to use the request header `X-Remote-User` it needs to be set to `HTTP_X_REMOTE_USER`.
