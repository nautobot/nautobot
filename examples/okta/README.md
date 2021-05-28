# Social Auth Pipeline Okta Group Sync Example

This example shows how to extend the Social Auth Pipeline to read groups from a groups claim in Okta and sync those with Nautobot.  

Create a python module with the `group_sync.py` file in it, this could be done as part of a plugin or as a standalone python module.

In the nautobot_config.py set the following values:

```python
SOCIAL_AUTH_OKTA_OAUTH2_SCOPE = ["groups"]

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
    "my_custom_module.okta.group_sync",
)
```

If the name of the claim from okta is different both the `SOCIAL_AUTH_OKTA_OAUTH2_SCOPE` and the script will need to be modified.  This example is provided as is and may very well be unique for your okta deployment.
