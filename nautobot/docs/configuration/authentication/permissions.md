# User Permissions

## Configuration

!!! note
    When a user logs in for the first time via remote user authentication or SSO, Nautobot will create a new user account for them.
    By default, this new user will not be a member of any group or have any permissions assigned. If you would like to create users with
    a default set of permissions, there are some additional variables to configure:

---

### REMOTE_AUTH_AUTO_CREATE_USER

Default: `False`

If set to `True`, local accounts will be automatically created for users authenticated via a remote service.

---

### REMOTE_AUTH_DEFAULT_GROUPS

Default: `[]` (Empty list)

The list of groups to assign a new user account when created using SSO authentication.

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

---

Please see [the object permissions page](../../administration/permissions.md) for more information.
