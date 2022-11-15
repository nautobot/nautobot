# Single Sign On

Nautobot supports several different authentication mechanisms including OAuth (1 and 2), OpenID, SAML, and others.
To accomplish this, Nautobot comes preinstalled with the [social-auth-app-django](https://python-social-auth.readthedocs.io/en/latest/configuration/django.html) Python module.

This module supports several [authentication backends](https://python-social-auth.readthedocs.io/en/latest/backends/index.html) by default including:

* Google
* Microsoft Azure Active Directory
* Okta
* [And many more...](https://python-social-auth.readthedocs.io/en/latest/backends/index.html#supported-backends)

## Installation

!!! warning
    Unless otherwise noted, all remaining steps in this document should all be performed as the `nautobot` user!

    Hint: Use `sudo -iu nautobot`

### Install Dependencies

If you are using OpenID Connect or SAML you will also need to install the extra dependencies for those.

#### OpenID Connect Dependencies

For OpenID connect, you'll need to install the `sso` Python extra.

```no-highlight
pip3 install "nautobot[sso]"
```

#### SAML Dependencies

For SAML, additional system-level dependencies are required so that the specialized XML libraries can be built and compiled for your system.

!!! note
    These instructions have only been certified on Ubuntu 20.04 at this time.

Install the system dependencies as `root`:

```no-highlight
sudo apt install -y libxmlsec1-dev libxmlsec1-openssl pkg-config
```

Install the `sso` Python extra as the `nautobot` user.

```no-highlight
pip3 install "nautobot[sso]"
```

Please see the SAML configuration guide below for an example of how to configure Nautobot to authenticate using SAML with Google as the identity provider.

## Configuration

### Authentication Backends

To use external authentication, you'll need to define `AUTHENTICATION_BACKENDS` in your `nautobot_config.py`.

* Insert the desired external authentication backend as the first item in the list. This step is key to properly redirecting when users click the login button.
* You must also ensure that `nautobot.core.authentication.ObjectPermissionBackend` is always the second item in the list. It is an error to exclude this backend.

!!! note
    It is critical that you include the `ObjectPermissionsBackend` provided by Nautobot after the desired backend so that object-level permissions features can work properly.

For example, if you wanted to use Google OAuth2 as your authentication backend:

```python
AUTHENTICATION_BACKENDS = [
    "social_core.backends.google.GoogleOAuth2",
    "nautobot.core.authentication.ObjectPermissionBackend",
]
```

!!! note
    Many backends have settings specific to that backend that are not covered in this guide. Please consult the documentation for your desired backend linked in the next section.

!!! warning
    You should only enable one social authentication authentication backend. It is technically possible to use multiple backends but we cannot officially support more than one at this time.

### Custom Authentication Backends

The default external authentication supported is [social-auth-app-django](https://python-social-auth.readthedocs.io/en/latest/configuration/django.html) as stated above. If you have developed your own external authentication backend, you will need to configure `SOCIAL_AUTH_BACKEND_PREFIX` to use your backend instead and correctly enable the SSO redirect when the login button is clicked. For example, if your custom authentication backend is available at `custom_auth.backends.custom.Oauth2`, you would set things as follows:

```python
SOCIAL_AUTH_BACKEND_PREFIX = "custom_auth.backends"

AUTHENTICATION_BACKENDS = [
    "custom_auth.backends.custom.Oauth2",
    "nautobot.core.authentication.ObjectPermissionBackend",
]
```

In the example above, `SOCIAL_AUTH_BACKEND_PREFIX` was set to `custom_auth.backends` within the `nautobot_config.py` for our custom authentication plugin we created (**custom_auth.backends.custom.Oauth2**). This will enable the SSO redirect for users when they click the login button.

---

### Select your Authentication Backend

You will need to select the correct social authentication module name for your desired method of external authentication. Please see [the official Python Social Auth documentation on supported backends](https://python-social-auth.readthedocs.io/en/latest/backends/index.html#supported-backends) for more the full list of backends and any specific configuration or required settings.

Some common backend module names include:

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
| [SAML](https://python-social-auth.readthedocs.io/en/latest/backends/saml.html) | `social_core.backends.saml.SAMLAuth` |

### User Permissions

By default, once authenticated, if the user has never logged in before a new user account will be created for the user.
This new user will not be a member of any group or have any permissions assigned. If you would like to create users with
a default set of permissions there are some additional variables to configure the permissions.

Please see the documentation on [`EXTERNAL_AUTH_DEFAULT_GROUPS`](../../configuration/optional-settings.md#external_auth_default_groups) and [`EXTERNAL_AUTH_DEFAULT_PERMISSIONS`](../../configuration/optional-settings.md#external_auth_default_permissions) for more information.

---

## Configuration Guides

The following guides are provided for some of the most common authentication methods.

### Okta

1. In the Okta admin portal, create a new *Web* application
2. Configure the application as follows:

    * *Base URIs*: should be the URI of your Nautobot application such as `https://nautobot.example.com`
    * *Login redirect URIs*: should be the Base URI plus `/complete/okta-openidconnect/` such as `https://nautobot.example.com/complete/okta-openidconnect/`
    * *Logout redirect URIs*: should be the Base URI plus `/disconnect/okta-openidconnect/` such as `https://nautobot.example.com/disconnect/okta-openidconnect/`

3. Once the application is configured in Okta, SSO can either be configured with OAuth2 or OpenID Connect (OIDC). When using an organization's authentication server OAuth2 is preferred; with custom Okta authentication backends, use OIDC.

#### Okta - OAuth2

Edit your `nautobot_config.py` as follows:

```python
AUTHENTICATION_BACKENDS = [
    "social_core.backends.okta.OktaOAuth2",
    "nautobot.core.authentication.ObjectPermissionBackend",
]

SOCIAL_AUTH_OKTA_OAUTH2_KEY = '<Client ID from Okta>'
SOCIAL_AUTH_OKTA_OAUTH2_SECRET = '<Client Secret From Okta>'
SOCIAL_AUTH_OKTA_OAUTH2_API_URL = 'https://<Okta URL>'
```

#### Okta - OpenID

Edit your `nautobot_config.py` as follows:

```python
AUTHENTICATION_BACKENDS = [
    "social_core.backends.okta_openidconnect.OktaOpenIdConnect",
    "nautobot.core.authentication.ObjectPermissionBackend",
]

SOCIAL_AUTH_OKTA_OPENIDCONNECT_KEY = '<Client ID from Okta>'
SOCIAL_AUTH_OKTA_OPENIDCONNECT_SECRET = '<Client Secret From Okta>'
SOCIAL_AUTH_OKTA_OPENIDCONNECT_API_URL = 'https://<Okta URL>/oauth2/<Authentication Server>'
```

The `/default` authentication server can be used for testing, however, it should not be used in production.

#### Okta - Additional Scopes

It is possible to get additional OAuth scopes from okta by adding them to the `SOCIAL_AUTH_{BACKEND}_SCOPE` list. For example to get the `groups` scope from Okta using OAuth2 add the following to your `nautobot_config.py`:

```python
SOCIAL_AUTH_OKTA_OAUTH2_SCOPE = ['groups']
```

for OpenID:

```python
SOCIAL_AUTH_OKTA_OPENIDCONNECT_SCOPE = ['groups']
```

In order to use this returned scope a custom function needs to be written and added to the `SOCIAL_AUTH_PIPELINE` as described in the [`python-social-auth` authentication pipeline documentation](https://python-social-auth.readthedocs.io/en/stable/pipeline.html).

An example to sync groups with Okta is provided in the [`examples/okta`](https://github.com/nautobot/nautobot/tree/develop/examples/okta) folder in the root of the Nautobot repository.

### Google - OAuth2

The following instructions guide you through the process of configuring Google for OAuth2 authentication.

!!! important
    Please note there is further guidance provided by [python-social-auth](https://python-social-auth.readthedocs.io/en/latest/backends/google.html#google-oauth2) as well as [Google](https://developers.google.com/identity/protocols/oauth2?csw=1). For more
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
AUTHENTICATION_BACKENDS = [
    "social_core.backends.google.GoogleOAuth2",
    "nautobot.core.authentication.ObjectPermissionBackend",
]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = '<Client ID from Google>'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = '<Secret ID from Google>'
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['openid']
```

### SAML

This guide will walk you through configuring Nautobot to authenticate using SAML with Google as the identity provider.

!!! important
    Please note that there is further guidance provided by [python-social-auth](https://python-social-auth.readthedocs.io/en/latest/backends/saml.html) and [Google](https://support.google.com/a/answer/6087519?hl=en). For more information please utilize these additional resources.

#### Prerequisites

!!! warning
    SAML will not work without end-to-end encryption. These requirements are not flexible.

Before you begin you will need the following:

* The fully-qualified domain name (FQDN) of your Nautobot host must be registered in DNS. For this example we will be using `nautobot.example.com`.
* A valid publicly trusted SSL certificate matching the FQDN of your host. You *cannot* use a self-signed certificate. Google validates this certificate to assert authenticity of SAML authentication requests.
* The name and email address for a technical point of contact. For this example we will use "Bob Jones, bob@example.com".
* The name and email address for a support point of contact. For this example we will use "Alice Jenkins, alice@example.com."

#### Setup SAML in Google

1. Visit the [Web and mobile apps](https://admin.google.com/ac/apps/unified) console in the Google Admin dashboard.
2. Follow Google's official document to [Set up your own custom SAML application](https://support.google.com/a/answer/6087519?hl=en), pausing at step 6.
3. From step 6 of the instructions, capture the **SSO URL**, **Entity ID**, and **Certificate**. You will use these in later steps to configure Nautobot. Each of these will be referred to as `GOOGLE_SSO_URL`, `GOOGLE_ENTITY_ID`, and `GOOGLE_CERTIFICATE` respectively.
4. Skip step 7 in the instructions, as that does not apply here because we will be configuring Nautobot directly.
5. For step 9 of the instructions under *Service provider details*, provide the following
    * **ACS URL**: `https://nautobot.example.com/complete/saml/`
    * **Entity ID:** `https://nautobot.example.com/`
    * **Start URL:** Leave this field blank
6. Skip step 10 in the instructions, as a signed response is not required.
7. For step 11 of the instructions, under *Name ID*, set the following:
    * **Name ID Format**: Select *EMAIL*
    * **Name ID:** Select *Basic Information > Primary Email*
8. For step 13 of the instructions, on the *Attribute mapping* page, add the following mappings for *Google Directory attributes* to *App attributes*:
    * *Primary email* --> `email`
    * *First name* --> `first_name`
    * *Last name* --> `last_name`
9. Click *Finish*

#### Configure Nautobot

There is a lot to configure to inform Nautobot how to integrate with SAML, so please provide the following configuration very carefully. All of these values must be correct in your `nautobot_config.py`.

!!! important
    Refer to the [official Python Social Auth documentation for required SAML configuration](https://python-social-auth.readthedocs.io/en/latest/backends/saml.html#required-configuration) if you run into any issues.

```python
# Django authentication backends
AUTHENTICATION_BACKENDS = [
    "social_core.backends.saml.SAMLAuth",
    "nautobot.core.authentication.ObjectPermissionBackend",
]

# The https FQDN to your Nautobot instance
SOCIAL_AUTH_SAML_SP_ENTITY_ID = "https://nautobot.example.com/"

# X.509 cert/key pair used for host verification are not used for this example because
# Nautobot is directly authenticating itself to Google. Set them to empty strings.
SOCIAL_AUTH_SAML_SP_PUBLIC_CERT = ""
SOCIAL_AUTH_SAML_SP_PRIVATE_KEY = ""

# A dictionary that contains information about your app. You must specify values for
# English at a minimum.
SOCIAL_AUTH_SAML_ORG_INFO = {
    "en-US": {
        "name": "Nautobot",
        "displayname": "Nautobot",
        "url": "https://nautobot.example.com",
    }
}

# Technical point of contact
SOCIAL_AUTH_SAML_TECHNICAL_CONTACT = {
    "givenName": "Bob Jones",
    "emailAddress": "bob@example.com"
}

# Support point of contact
SOCIAL_AUTH_SAML_SUPPORT_CONTACT = {
    "givenName": "Alice Jenkins",
    "emailAddress": "alice@example.com"
}

# The Entity ID URL for Google from step 3
GOOGLE_ENTITY_ID = "<Entity ID from Google>"

# The SSO URL for Google from step 3
GOOGLE_SSO_URL = "<SSO URL from Google>"

# The Certificate for Google from step 3
GOOGLE_CERTIFICATE = "<Certificate from Google>"

# The most important setting. List the Entity ID, SSO URL, and x.509 public key certificate
# for each provider that you app wants to support. We are only supporting Google for this
# example.
SOCIAL_AUTH_SAML_ENABLED_IDPS = {
    "google": {
        "entity_id": GOOGLE_ENTITY_ID,
        "url": GOOGLE_SSO_URL,
        "x509cert": GOOGLE_CERTIFICATE,
        # These are used to map to User object fields in Nautobot using Google
        # attribute fields we configured in step 8 of "Setup SAML in Google".
        "attr_user_permanent_id": "email",
        "attr_first_name": "first_name",
        "attr_last_name": "last_name",
        "attr_username": "email",
        "attr_email": "email",
    }
}

# Required for correctly redirecting when behind SSL proxy (NGINX). You may or may not need
# these depending on your production deployment. They are provided here just in case.
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

#### Enable SAML in Google

Now that you've configured both Google and Nautobot for SAML, you still need to enable SAML for your users in your Google domain.

On Google's official site to [Set up your own custom SAML application](https://support.google.com/a/answer/6087519?hl=en), scroll down to **Turn on your SAML app** and follow the remaining instructions to enable and verify SAML in Google.

#### Login with SAML

Note the provider entry we configured in `SOCIAL_AUTH_SAML_ENABLED_IDPS` as `google`. This will be used to login and will be referenced in the query parameter using `idp=google`. For example `/login/saml/?idp=google`.

This should be the URL that is mapped to the "Log in" button on the top right of the index page when you navigate to Nautobot in your browser. Clicking this link should automatically redirect you to Google, ask you to "Choose an account", log you in and redirect you back to the Nautobot home page. Your email address will also be your username.

---

Be sure to configure [`EXTERNAL_AUTH_DEFAULT_GROUPS`](../../configuration/optional-settings.md#external_auth_default_groups) and [`EXTERNAL_AUTH_DEFAULT_PERMISSIONS`](../../configuration/optional-settings.md#external_auth_default_permissions) next.

### Azure AD

1. In the Azure admin portal, search for and select *Azure Active Directory*.
2. Under *Manage*, select *App registrations -> New registration*.
3. Configure the application as follows:

    * *Name*: This is the user-facing display name for the app.
    * *Supported account types*: This specifies the AD directories that you're allowing to authenticate with this app.
    * *Redirect URIs*: Don't fill this out yet, it will be configured in the following steps.

4. Once the application is configured in Azure, you'll be shown the app registration's *Overview* page. Please take note of the *Application (client) ID* for use later. SSO with Azure can either be configured with OAuth2 or OpenID Connect (OIDC). When using an organization's authentication server OAuth2 is preferred; with custom Azure authentication backends, use OIDC.
5. From the App registration page, click on *Authentication*. Under *Platform configurations*, select *Add a platform* and select *Web*.
6. Click on the *Add a Redirect URI* link on the page and configure it as follows:

    * *Redirect URIs*: should be the Base URI plus `/complete/azuread-oauth2/` such as `https://nautobot.example.com/complete/azuread-oauth2/`

7. Once the Redirect URI is set, the last thing you'll need is to generate a *client secret*. To do so, click on *Certificates & secrets* and then the *New client secret* option. At this point you'll need to specify the expiration for the secret. Microsoft recommends less than 12 months with a maximum of 24 months as an option. Ensure you make a note of the secret that's generated for the next step.

8. With the client secret generated, edit your `nautobot_config.py` as follows:

#### Azure AD - OAuth2

If your app is linked to the common tenant, you'll want to edit your `nautobot_config.py` as follows:

```python
AUTHENTICATION_BACKENDS = [
    "social_core.backends.azuread.AzureADOAuth2",
    "nautobot.core.authentication.ObjectPermissionBackend",
]

SOCIAL_AUTH_AZUREAD_OAUTH2_KEY = "<Client ID from Azure>"
SOCIAL_AUTH_AZUREAD_OAUTH2_SECRET = "<Client Secret From Azure>"
```

#### Azure - Tenant Support

If your app is linked to a specific tenant instead of the common tenant, you'll want to edit your `nautobot_config.py` as follows:

```python
AUTHENTICATION_BACKENDS = [
    "social_core.backends.azuread.AzureADTenantOAuth2",
    "nautobot.core.authentication.ObjectPermissionBackend",
]

SOCIAL_AUTH_AZUREAD_TENANT_OAUTH2_KEY = "<Client ID from Azure>"
SOCIAL_AUTH_AZUREAD_TENANT_OAUTH2_SECRET = "<Client Secret From Azure>"
SOCIAL_AUTH_AZUREAD_TENANT_OAUTH2_TENANT_ID = "<Tenant ID from Azure>"
```

---

With those settings in place your users should be able to authenticate against Azure AD and successfully login to Nautobot. However, that user will not be placed in any groups or given any permissions. In order to do so, you'll need to utilize a script to synchronize the groups passed from Azure to Nautobot after authentication succeeds. Any group permissions will need to be set manually in the Nautobot admin panel.

An example to sync groups with Azure is provided in the [`examples/azure_ad`](https://github.com/nautobot/nautobot/tree/main/examples/azure_ad) folder in the root of the Nautobot repository.
