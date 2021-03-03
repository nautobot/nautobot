# Single Sign On

Nautobot supports several different authentication mechanisms including OAuth (1 and 2), OpenID, SAML, and others.
To accomplish this the [social-auth-app-django](https://python-social-auth.readthedocs.io/en/latest/configuration/django.html) python module is used.

This module supports several [authentication backends](https://python-social-auth.readthedocs.io/en/latest/backends/index.html)
by default including:

* Google
* Microsoft Azure Active Directory
* Okta
* [And many more...](https://python-social-auth.readthedocs.io/en/latest/backends/index.html#supported-backends)

## Installation

!!! warning
    This and all remaining steps in this document should all be performed as the `nautobot` user!

    Hint: Use `sudo su - nautobot` 

### Install Dependencies

```shell
$ pip3 install social-auth-app-django
```

### Extra Dependencies

If you are using OpenID Connect or SAML you will also need to include the extra dependencies for those.

#### OpenID Connect

```shell
$ pip3 install "social-auth-core[openidconnect]"
```

#### SAML

```shell
$ pip3 install "social-auth-core[saml]"
```

!!! note
    You should only enable one social auth authentication backend.  Please see the
    [full documentation on supported backends](https://python-social-auth.readthedocs.io/en/latest/backends/index.html#supported-backends).

## Configuration

The following settings are required and can be made with some simple additions to your `nautobot_config.py`.

---

### SOCIAL_AUTH_ENABLED

Default: `False`

Enables the social auth backend, this setting is required to be enabled to use the Social Auth SSO for authentication:

---

### SOCIAL_AUTH_MODULE

The Social Auth module name, see [the official backend documentation](https://python-social-auth.readthedocs.io/en/latest/backends/index.html#supported-backends) for more information.  Some common backend module names include:

| Backend | Social Auth Backend Module Name |
|---------|---------------------------------|
| [Microsoft Azure Active Directory](https://python-social-auth.readthedocs.io/en/latest/backends/azuread.html) | `social_core.backends.azuread.AzureADOAuth2` |
| | `social_core.backends.azuread_b2c.AzureADB2COAuth2` |
| | `social_core.backends.azuread_tenant.AzureADTenantOAuth2` |
| | `social_core.backends.azuread_tenant.AzureADV2TenantOAuth2` |
| [Google](https://python-social-auth.readthedocs.io/en/latest/backends/google.html) | `social_core.backends.gae.GoogleAppEngineAuth` |
| | `social_core.backends.google.GoogleOAuth2` |
| | `social_core.backends.google.GoogleOAuth` |
| | `social_core.backends.google_openidconnect.GoogleOpenIdConnect` |
| [Okta](https://python-social-auth.readthedocs.io/en/latest/backends/okta.html) | `social_core.backends.okta.OktaOAuth2` |
| | `social_core.backends.okta_openidconnect.OktaOpenIdConnect` |

---

### SOCIAL_AUTH_URL_NAMESPACE

Default: `sso`

The [Django URL](https://docs.djangoproject.com/en/3.1/topics/http/urls/#url-namespaces) namespace to use for the social auth module. The default is typically fine and should only be changed if absolutely necessary.

## User Permissions

By default, once authenticated, if the user has never logged in before a new user account will be created for the user.
This new user will not be a member of any group or have any permissions assigned. If you would like to create users with
a default set of permissions there are some additional variables to configure the permissions:

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

Please see [the object permissions page](../../administration/permissions.md) for more information.

---

### SOCIAL_AUTH_DEFAULT_SUPERUSER

Default: `False`

If set to `True`, local accounts created by the social auth module will have the Django superuser default set of privileges.  This means the user
will be able to create, read, update, and delete all objects in Nautobot but will not have access to the Django admin pages.

---

### SOCIAL_AUTH_DEFAULT_STAFF

Default: `False`

If set to `True`, local accounts created by the social auth module will have the Django staff default set of privileges.  This means the user
will be able to access the Django admin pages.

## Examples

Below are some example configurations for common authentication backends, for details on configuring
other backends please see the [full documentation on supported backends](https://python-social-auth.readthedocs.io/en/latest/backends/index.html#supported-backends).

### Okta - OpenID

1. In the Okta admin portal, create a new *Web* application
2. Configure the application as follows:

    * *Base URIs*: should be the URI of your Nautobot application such as `https://nautobot.example.com`
    * *Login redirect URIs*: should be the Base URI plus `/complete/okta-openidconnect/` such as `https://nautobot.example.com/complete/okta-openidconnect/`
    * *Logout redirect URIs*: should be the Base URI plus `/disconnect/okta-openidconnect/` such as `https://nautobot.example.com/disconnect/okta-openidconnect/`

3. Once the application is configured in Okta, edit your `nautobot_config.py` as follows:

```python
SOCIAL_AUTH_ENABLED = True
SOCIAL_AUTH_MODULE = 'social_core.backends.okta_openidconnect.OktaOpenIdConnect'

SOCIAL_AUTH_OKTA_OPENIDCONNECT_KEY = '<Client ID from Okta>'
SOCIAL_AUTH_OKTA_OPENIDCONNECT_SECRET = '<Client Secret From Okta>'
SOCIAL_AUTH_OKTA_OPENIDCONNECT_API_URL = 'https://<Okta URL>/oauth2/<Authentication Server>'
```

The default authentication server can be used for testing, however, it should not be used in production.

### Google - OAuth2

The following instructions guide you through the process of configuring Google for OAuth2 authentication.
Please note there is further guidance provided by
[python-social-auth](https://python-social-auth.readthedocs.io/en/latest/backends/google.html#google-oauth2)
as well as [Google](https://developers.google.com/identity/protocols/oauth2?csw=1) themselves, for more
information please utilize these additional resources.

1. In the [Google API Console](https://console.developers.google.com/) create a new project or select an existing one.
2. Select *OAuth consent screen* from the menu on the left side of the page
3. For *User Type* select *Internal* and click *Create*
4. Configure as follows:

    * *App name*: Acme Corp Nautobot
    * *User support email*: select an email
    * *App logo*: The Nautobot logo can be found at `nautobot/project-static/img/nautobot_logo.png`

5. Click *Save and Continue*
6. No additional scopes are needed click *Save and Continue*
7. Select *Credentials* from the menu on the left side of the page
8. Click *+ Create Credentials* at the top of the page and select *OAuth client ID*
9. Configure as follows:

    * *Application type*: Web application
    * *Name*: Nautobot
    * *Authorized redirect URIs*: should be the Nautobot URL plus `/complete/google-oauth2/` for example `https://nautobot.example.com/complete/google-oauth2/`

10. Click Create
11. Edit your `nautobot_config.py` as follows:

```python
SOCIAL_AUTH_ENABLED = True
SOCIAL_AUTH_MODULE = 'social_core.backends.google.GoogleOAuth2'

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = '<Client ID from Google>'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = '<Secret ID from Google>'
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['openid']
```
