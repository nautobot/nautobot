# LDAP Authentication

This guide explains how to implement LDAP authentication using an external server. User authentication will fall back to built-in Django users in the event of a failure.

## Install Requirements

### Install System Packages

On Ubuntu:

```no-highlight
sudo apt install -y libldap-dev libsasl2-dev
```

On CentOS:

```no-highlight
sudo dnf install -y openldap-devel
```

### Install django-auth-ldap

!!! warning
    This and all remaining steps in this document should all be performed as the `nautobot` user!

    Hint: Use `sudo -iu nautobot`

Activate the Python virtual environment and install the `django-auth-ldap` package using pip:

```no-highlight
source /opt/nautobot/bin/activate
pip3 install "nautobot[ldap]"
```

Once installed, add the package to `local_requirements.txt` to ensure it is re-installed during future rebuilds of the virtual environment:

```no-highlight
echo "nautobot[ldap]" >> /opt/nautobot/local_requirements.txt
```

## Configuration

Enable the LDAP authentication backend by adding the following to your `nautobot_config.py`:

!!! note
    It is critical that you include the `ObjectPermissionsBackend` provided by Nautobot after the `LDAPBackend` so that object-level permissions features can work properly.

```python
AUTHENTICATION_BACKENDS = [
    'django_auth_ldap.backend.LDAPBackend',
    'nautobot.core.authentication.ObjectPermissionBackend',
]
```

### General Server Configuration

Define all of the parameters required below in your `nautobot_config.py`. Complete documentation of all `django-auth-ldap` configuration options is included in the project's [official documentation](http://django-auth-ldap.readthedocs.io/).

!!! info
    When using Windows Server 2012 you may wish to use the [Global Catalog](https://docs.microsoft.com/en-us/windows/win32/ad/global-catalog) by specifying a port on `AUTH_LDAP_SERVER_URI`. Use `3269` for secure (`ldaps://`), or `3268` for non-secure.

```python
import ldap

# Server URI
AUTH_LDAP_SERVER_URI = "ldap://ad.example.com"

# The following may be needed if you are binding to Active Directory.
AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: 0
}

# Set the DN and password for the Nautobot service account.
AUTH_LDAP_BIND_DN = "CN=NAUTOBOTSA, OU=Service Accounts,DC=example,DC=com"
AUTH_LDAP_BIND_PASSWORD = "demo"
```

### Encryption Options

It is recommended when using LDAP to use STARTTLS, however SSL can also be used.

#### TLS Options

STARTTLS can be configured by setting `AUTH_LDAP_START_TLS = True` and using the `ldap://` URI scheme.

```python
AUTH_LDAP_SERVER_URI = "ldap://ad.example.com"
AUTH_LDAP_START_TLS = True
```

#### SSL Options

SSL can also be used by using the `ldaps://` URI scheme.

```python
AUTH_LDAP_SERVER_URI = "ldaps://ad.example.com"
```

#### Certificate Validation

When using either TLS or SSL it is necessary to validate the certificate from your LDAP server. Copy your CA cert to `/opt/nautobot/ca.pem`.

```python
# Set the path to the trusted CA certificates and create a new internal SSL context.
AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_X_TLS_CACERTFILE: "/opt/nautobot/ca.pem",
    ldap.OPT_X_TLS_NEWCTX: 0
}
```

If you prefer you can ignore the certificate, however, this is only recommended in development and not production.

```python
# WARNING: You should not do this in production!
AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_NEVER,
}
```

Additional ldap connection options can be found in the [python-ldap documentation](https://www.python-ldap.org/en/python-ldap-3.3.0/reference/ldap.html?highlight=cacert#options).

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

#### Searching in Multiple LDAP Groups

Define the user-groups in your environment, such as a `*.env` file (delimiter `';'`):

```python
# Groups to search for user objects. "(sAMAccountName=%(user)s),..."
NAUTOBOT_AUTH_LDAP_USER_SEARCH_DN=OU=IT-Admins,OU=special-users,OU=Acme-User,DC=Acme,DC=local;OU=Infrastruktur,OU=IT,OU=my-location,OU=User,OU=Acme-User,DC=Acme,DC=local
```

Import LDAPSearchUnion in `nautobot_config.py`, and replace the AUTH_LDAP_USER_SEARCH command from above:

```python
from django_auth_ldap.config import ..., LDAPSearchUnion

# ...

AUTH_LDAP_USER_SEARCH_DN = os.getenv("NAUTOBOT_AUTH_LDAP_USER_SEARCH_DN", "")

if AUTH_LDAP_USER_SEARCH_DN != "":
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

## Multiple LDAP Server Support

Multiple servers can be supported in `django-auth-ldap` by the use of additional LDAP backends, as described in the library's [documentation](https://django-auth-ldap.readthedocs.io/en/latest/multiconfig.html).

In order to define and load additional backends into Nautobot a plugin can be used. This plugin will allow the backend(s) to be loaded into the Django settings for use within the `nautobot_config.py` file. At the simplest form the plugin should have a custom backend(s) defined:

```python
# my_customer_backends.py

from django_auth_ldap.backend import LDAPBackend

class LDAPBackendSecondary(LDAPBackend):
    settings_prefix = "AUTH_LDAP_SECONDARY_"
```

If the plugin is named `nautobot_ldap_plugin`, the following snippet could be used to load the additional LDAP backend:

```python
# nautobot_config.py

AUTHENTICATION_BACKENDS = [
    'django_auth_ldap.backend.LDAPBackend',
    'nautobot_ldap_plugin.my_customer_backends.LDAPBackendSecondary',  # path to the custom LDAP Backend
    'nautobot.core.authentication.ObjectPermissionBackend',
]
```

Once the custom backend is loaded into the settings all the configuration items mentioned previously need to be completed for each server. As a simplified example defining the URIs would be accomplished by the following two lines in the `nautobot_config.py` file. A similar approach would be done to define the rest of the settings.

```python
# nautobot_config.py

# Server URI which uses django_auth_ldap.backend.LDAPBackend
AUTH_LDAP_SERVER_URI = "ldap://ad.example.com"

# Server URI which uses nautobot_ldap_plugin.my_customer_backends.LDAPBackendSecondary
AUTH_LDAP_SECONDARY_SERVER_URI = "ldap://secondary-ad.example.com"
```

!!! info
    In this example the default LDAPBackend was still used as the first LDAP server, which utilized the `AUTH_LDAP_*` environment variables. It is also possible to remove the default backend and create multiple custom backends instead to normalize the environment variable naming scheme.

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
