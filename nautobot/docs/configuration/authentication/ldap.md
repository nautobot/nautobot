# LDAP Authentication

This guide explains how to implement LDAP authentication using an external server. User authentication will fall back to built-in Django users in the event of a failure.

## Install Requirements

### Install System Packages

!!! danger
    FIXME(jathan): With `wheel` packages asserted, let's make doubly sure these development libraries even need to be installed anymore.

On Ubuntu:

```no-highlight
$ sudo apt install -y libldap2-dev libsasl2-dev libssl-dev
```

On CentOS:

```no-highlight
$ sudo dnf install -y openldap-devel
```

### Install django-auth-ldap

!!! warning
    This and all remaining steps in this document should all be performed as the `nautobot` user!

    Hint: Use `sudo -iu nautobot`

Activate the Python virtual environment and install the `django-auth-ldap` package using pip:

```no-highlight
$ source /opt/nautobot/bin/activate
(nautobot) $ pip3 install django-auth-ldap
```

Once installed, add the package to `local_requirements.txt` to ensure it is re-installed during future rebuilds of the virtual environment:

```no-highlight
(nautobot) $ echo django-auth-ldap >> /opt/nautobot/local_requirements.txt
```

## Configuration

Enable the LDAP authentication backend by adding the following to your `nautobot_config.py`:

!!! note
    It is critical that you include the `ObjectPermissionsBackend` provided by
    Nautobot after the `LDAPBackend` so that object-level permissions features can work properly.

```python
AUTHENTICATION_BACKENDS = [
    'django_auth_ldap.backend.LDAPBackend',
    'nautobot.core.authentication.ObjectPermissionBackend',
]
```

### General Server Configuration

Define all of the parameters required below in your `nautobot_config.py`. Complete documentation of all `django-auth-ldap` configuration options is included in the project's [official documentation](http://django-auth-ldap.readthedocs.io/).

!!! info
    When using Windows Server 2012 you may need to specify a port on `AUTH_LDAP_SERVER_URI`. Use `3269` for secure, or `3268` for non-secure.

```python
import ldap

# Server URI
AUTH_LDAP_SERVER_URI = "ldaps://ad.example.com"

# The following may be needed if you are binding to Active Directory.
AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: 0
}

# Set the DN and password for the Nautobot service account.
AUTH_LDAP_BIND_DN = "CN=NAUTOBOTSA, OU=Service Accounts,DC=example,DC=com"
AUTH_LDAP_BIND_PASSWORD = "demo"

# Include this setting if you want to ignore certificate errors. This might be needed to accept a self-signed cert.
# Note that this is a Nautobot-specific setting which sets:
#     ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
LDAP_IGNORE_CERT_ERRORS = True
```

### TLS Options

STARTTLS can be configured by setting `AUTH_LDAP_START_TLS = True` and using the `ldap://` URI scheme.

Apply TLS settings to the internal SSL context on nautobot by configuring `ldap.OPT_X_TLS_NEWCTX` with value `0`.

```
AUTH_LDAP_SERVER_URI = "ldap://ad.example.com"
AUTH_LDAP_START_TLS = True
# Set the path to the trusted CA certificates and create a new internal SSL context.
AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_X_TLS_CACERTFILE: "/path/to/ca.pem",
    ldap.OPT_X_TLS_NEWCTX: 0
}
LDAP_IGNORE_CERT_ERRORS = False
```

### User Authentication

!!! info
    When using Windows Server 2012, `AUTH_LDAP_USER_DN_TEMPLATE` should be set to None.

```python
from django_auth_ldap.config import LDAPSearch

# This search matches users with the sAMAccountName equal to the provided username. This is required if the user's
# username is not in their DN (Active Directory).
AUTH_LDAP_USER_SEARCH = LDAPSearch("ou=Users,dc=example,dc=com",
                                    ldap.SCOPE_SUBTREE,
                                    "(sAMAccountName=%(user)s)")

# If a user's DN is producible from their username, we don't need to search.
AUTH_LDAP_USER_DN_TEMPLATE = "uid=%(user)s,ou=users,dc=example,dc=com"

# You can map user attributes to Django attributes as so.
AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail"
}
```

The following snippet shows how to search for users in multiple LDAP groups:

- Define the user-groups in *.env file (delimiter `';'`)

    ```bash
    # Groups to search for user objects. "(sAMAccountName=%(user)s),..."
    NAUTOBOT_AUTH_LDAP_USER_SEARCH_DN=OU=IT-Admins,OU=special-users,OU=Acme-User,DC=Acme,DC=local;OU=Infrastruktur,OU=IT,OU=my-location,OU=User,OU=Acme-User,DC=Acme,DC=local
    ```

- Import LDAPSearchUnion in `nautobot_config.py`

    ```python
    from django_auth_ldap.config import ..., LDAPSearchUnion
    ```

- In `nautobot_config.py` replace the AUTH_LDAP_USER_SEARCH command from above with:

    ```bash
    user_search_dn_list = str(AUTH_LDAP_USER_SEARCH_DN).split(";")
    ldapsearch_objects = []
    for sdn in user_search_dn_list:
        ldapsearch_objects.append(LDAPSearch(sdn.strip(), ldap.SCOPE_SUBTREE, "(sAMAccountName=%(user)s)"))
    AUTH_LDAP_USER_SEARCH = LDAPSearchUnion(*ldapsearch_objects)
    ```

### User Groups for Permissions

!!! info
    When using Microsoft Active Directory, support for nested groups can be activated by using `NestedGroupOfNamesType()` instead of `GroupOfNamesType()` for `AUTH_LDAP_GROUP_TYPE`. You will also need to modify the import line to use `NestedGroupOfNamesType` instead of `GroupOfNamesType` .

```python
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType

# This search ought to return all groups to which the user belongs. django_auth_ldap uses this to determine group
# hierarchy.
AUTH_LDAP_GROUP_SEARCH = LDAPSearch("dc=example,dc=com", ldap.SCOPE_SUBTREE,
                                    "(objectClass=group)")
AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()

# Define a group required to login.
AUTH_LDAP_REQUIRE_GROUP = "CN=NAUTOBOT_USERS,DC=example,DC=com"

# Define special user types using groups. Exercise great caution when assigning superuser status.
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    "is_active": "cn=active,ou=groups,dc=example,dc=com",
    "is_staff": "cn=staff,ou=groups,dc=example,dc=com",
    "is_superuser": "cn=superuser,ou=groups,dc=example,dc=com"
}

# For more granular permissions, we can map LDAP groups to Django groups.
AUTH_LDAP_FIND_GROUP_PERMS = True

# Cache groups for one hour to reduce LDAP traffic
AUTH_LDAP_CACHE_TIMEOUT = 3600

```

* `is_active` - All users must be mapped to at least this group to enable authentication. Without this, users cannot log in.
* `is_staff` - Users mapped to this group are enabled for access to the administration tools; this is the equivalent of checking the "staff status" box on a manually created user. This doesn't grant any specific permissions.
* `is_superuser` - Users mapped to this group will be granted superuser status. Superusers are implicitly granted all permissions.

!!! warning
    Authentication will fail if the groups (the distinguished names) do not exist in the LDAP directory.

## Troubleshooting LDAP

`systemctl restart nautobot` restarts the Nautobot service, and initiates any changes made to `nautobot_config.py`. If there are syntax errors present, the Nautobot process will not spawn an instance, and errors should be logged to `/var/log/messages`.

For troubleshooting LDAP user/group queries, add or merge the following [logging](../../configuration/optional-settings.md#logging) configuration to `nautobot_config.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'nautobot_auth_log': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/opt/nautobot/logs/django-ldap-debug.log',
            'maxBytes': 1024 * 500,
            'backupCount': 5,
        },
    },
    'loggers': {
        'django_auth_ldap': {
            'handlers': ['nautobot_auth_log'],
            'level': 'DEBUG',
        },
    },
}
```

Ensure the file and path specified in logfile exist and are writable and executable by the application service account. Restart the nautobot service and attempt to log into the site to trigger log entries to this file.

---

Be sure to configure [`EXTERNAL_AUTH_DEFAULT_GROUPS`](../../configuration/optional-settings.md#external_auth_default_groups) and [`EXTERNAL_AUTH_DEFAULT_PERMISSIONS`](../../configuration/optional-settings.md#external_auth_default_permissions) next.
