# Social Auth Pipeline AzureAD Group Sync Example

This example shows how to extend the Social Auth Pipeline to read groups from a groups claim in AzureAD and sync those with Nautobot.  

Create a python module with the provided `group_sync.py` file in it. This could be done as part of a plugin or as a standalone python module.

In the `nautobot_config.py` set the following values with the settings from Azure:

```python
AUTHENTICATION_BACKENDS = [
    "social_core.backends.azuread.AzureADOAuth2",
    "nautobot.core.authentication.ObjectPermissionBackend",
]

SOCIAL_AUTH_AZUREAD_OAUTH2_KEY = ""
SOCIAL_AUTH_AZUREAD_OAUTH2_SECRET = ""
SOCIAL_AUTH_AZUREAD_TENANT_OAUTH2_TENANT_ID = ""
SOCIAL_AUTH_AZUREAD_OAUTH2_RESOURCE = ""

SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
    "my_custom_module.azuread.group_sync",
)
```

If the name of the name of your Superuser and Staff groups vary from default you'll need to update the script accordingly.  This example is provided "as is" and may very well be unique for your Azure deployment.
