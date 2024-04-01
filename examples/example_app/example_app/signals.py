"""Signal handlers for the example_app."""

EXAMPLE_APP_CUSTOM_FIELD_DEFAULT = "Default value"
EXAMPLE_APP_CUSTOM_FIELD_NAME = "example_app_auto_custom_field"  # Note underscores rather than dashes!


def nautobot_database_ready_callback(sender, *, apps, **kwargs):
    """
    Callback function triggered by the nautobot_database_ready signal when the Nautobot database is fully ready.

    This function is connected to that signal in ExampleAppConfig.ready().

    An App could use this callback to add any records to the database that it requires for proper operation,
    such as:

    - Relationship definitions
    - CustomField definitions
    - Webhook definitions
    - etc.

    Args:
        sender (NautobotAppConfig): The ExampleAppConfig instance that was registered for this callback
        apps (django.apps.apps.Apps): Use this to look up model classes as needed
        **kwargs: See https://docs.djangoproject.com/en/3.1/ref/signals/#post-migrate for additional args
    """
    # Ensure that a desired custom field exists on the Location model
    ContentType = apps.get_model("contenttypes", "ContentType")
    Location = apps.get_model("dcim", "Location")
    CustomField = apps.get_model("extras", "CustomField")

    from nautobot.extras.choices import CustomFieldTypeChoices

    if hasattr(CustomField, "slug"):
        field, _ = CustomField.objects.update_or_create(
            slug=EXAMPLE_APP_CUSTOM_FIELD_NAME,
            defaults={
                "type": CustomFieldTypeChoices.TYPE_TEXT,
                "label": "Example App Automatically Added Custom Field",
                "default": EXAMPLE_APP_CUSTOM_FIELD_DEFAULT,
            },
        )
    else:
        field, _ = CustomField.objects.update_or_create(
            key=EXAMPLE_APP_CUSTOM_FIELD_NAME,
            defaults={
                "type": CustomFieldTypeChoices.TYPE_TEXT,
                "label": "Example App Automatically Added Custom Field",
                "default": EXAMPLE_APP_CUSTOM_FIELD_DEFAULT,
            },
        )
    field.content_types.set([ContentType.objects.get_for_model(Location)])
