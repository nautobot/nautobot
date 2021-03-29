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

    Hint: Use `sudo -iu nautobot`

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


### Okta - OpenID

1. In the Okta admin portal, create a new *Web* application
2. Configure the application as follows:

    * *Base URIs*: should be the URI of your Nautobot application such as `https://nautobot.example.com`
    * *Login redirect URIs*: should be the Base URI plus `/complete/okta-openidconnect/` such as `https://nautobot.example.com/complete/okta-openidconnect/`
    * *Logout redirect URIs*: should be the Base URI plus `/disconnect/okta-openidconnect/` such as `https://nautobot.example.com/disconnect/okta-openidconnect/`

3. Once the application is configured in Okta, edit your `nautobot_config.py` as follows:

```python
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
SOCIAL_AUTH_MODULE = 'social_core.backends.google.GoogleOAuth2'

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = '<Client ID from Google>'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = '<Secret ID from Google>'
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['openid']
```
---

Be sure to configure [`EXTERNAL_AUTH_DEFAULT_GROUPS`](../../configuration/optional-settings.md#external_auth_default_groups) and [`EXTERNAL_AUTH_DEFAULT_PERMISSIONS`](../../configuration/optional-settings.md#external_auth_default_permissions) next.
