from django.db import migrations
import uuid

from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.utilities.utils import serialize_object


def migrate_history(apps, schema_editor):
    """
    Migrate Django LogEntry objects to Nautobot ObjectChange objects.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    CustomField = apps.get_model("extras", "CustomField")
    LogEntry = apps.get_model("admin", "LogEntry")
    ObjectChange = apps.get_model("extras", "ObjectChange")
    custom_field_type = ContentType.objects.get_for_model(CustomField)
    for custom_field in CustomField.objects.all():
        for log_entry in LogEntry.objects.filter(content_type=custom_field_type, object_id=custom_field.id).order_by(
            "action_time"
        ):
            if log_entry.is_addition():
                action = ObjectChangeActionChoices.ACTION_CREATE
            if log_entry.is_change():
                action = ObjectChangeActionChoices.ACTION_UPDATE
            if log_entry.is_deletion():
                action = ObjectChangeActionChoices.ACTION_DELETE
            # Unfortunately, we can't get the serialized_object before the change so the calculated Difference
            # will be empty.  So we capture the Django change message to include in object_data to provide some
            # representation of the change
            object_data = serialize_object(custom_field)
            # object_data needs ascii, remove unicode characters from change message
            object_data["changelog_message"] = log_entry.get_change_message().encode("ascii", "ignore").decode()
            object_change = ObjectChange(
                user=log_entry.user,
                action=action,
                changed_object=custom_field,
                # Django LogEntry messages don't contain a request id so we make one up
                request_id=uuid.uuid4(),
                object_data=object_data,
            )
            object_change.validated_save()
            # The time is forced to now on creation of an ObjectChange object, so update it to the action time
            object_change.time = log_entry.action_time
            object_change.save()


class Migration(migrations.Migration):

    dependencies = [
        ("extras", "0020_customfield_changelog"),
    ]

    operations = [
        migrations.RunPython(migrate_history),
    ]
