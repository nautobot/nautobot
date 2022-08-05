"""Signal handlers for the example example_plugin."""


def nautobot_database_ready_callback(sender, *, apps, **kwargs):
    """
    Callback function triggered by the nautobot_database_ready signal when the Nautobot database is fully ready.

    This function is connected to that signal in ExamplePluginConfig.ready().

    A plugin could use this callback to add any records to the database that it requires for proper operation,
    such as:

    - Relationship definitions
    - CustomField definitions
    - Webhook definitions
    - etc.

    Args:
        sender (PluginConfig): The ExamplePluginConfig instance that was registered for this callback
        apps (django.apps.apps.Apps): Use this to look up model classes as needed
        **kwargs: See https://docs.djangoproject.com/en/3.1/ref/signals/#post-migrate for additional args
    """
    # Ensure that a desired custom field exists on the Site model
    ContentType = apps.get_model("contenttypes", "ContentType")
    Site = apps.get_model("dcim", "Site")
    CustomField = apps.get_model("extras", "CustomField")

    from nautobot.extras.choices import CustomFieldTypeChoices

    field, _ = CustomField.objects.update_or_create(
        name="example_plugin_auto_custom_field",  # Effectively a slug, will go away in a future Nautobot release
        slug="example_plugin_auto_custom_field",  # Note underscores rather than dashes!
        defaults={
            "type": CustomFieldTypeChoices.TYPE_TEXT,
            "label": "Example Plugin Automatically Added Custom Field",
            "default": "Default value",
        },
    )
    field.content_types.set([ContentType.objects.get_for_model(Site)])
