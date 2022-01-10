from django.db import migrations
from django.utils.text import get_text_list
from django.utils.translation import gettext
import json
import uuid

from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.utilities.utils import serialize_object

ADDITION = 1
CHANGE = 2
DELETION = 3


# Redefine get_change_message here as functions are not available with apps.get_model
def get_change_message(log_entry):
    """
    If log_entry.change_message is a JSON structure, interpret it as a change
    string, properly translated.
    """
    if log_entry.change_message and log_entry.change_message[0] == "[":
        try:
            change_message = json.loads(log_entry.change_message)
        except json.JSONDecodeError:
            return log_entry.change_message
        messages = []
        for sub_message in change_message:
            if "added" in sub_message:
                if sub_message["added"]:
                    sub_message["added"]["name"] = gettext(sub_message["added"]["name"])
                    messages.append(gettext("Added {name} “{object}”.").format(**sub_message["added"]))
                else:
                    messages.append(gettext("Added."))

            elif "changed" in sub_message:
                sub_message["changed"]["fields"] = get_text_list(
                    [gettext(field_name) for field_name in sub_message["changed"]["fields"]], gettext("and")
                )
                if "name" in sub_message["changed"]:
                    sub_message["changed"]["name"] = gettext(sub_message["changed"]["name"])
                    messages.append(gettext("Changed {fields} for {name} “{object}”.").format(**sub_message["changed"]))
                else:
                    messages.append(gettext("Changed {fields}.").format(**sub_message["changed"]))

            elif "deleted" in sub_message:
                sub_message["deleted"]["name"] = gettext(sub_message["deleted"]["name"])
                messages.append(gettext("Deleted {name} “{object}”.").format(**sub_message["deleted"]))

        change_message = " ".join(msg[0].upper() + msg[1:] for msg in messages)
        return change_message or gettext("No fields changed.")
    else:
        return log_entry.change_message


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
            if log_entry.action_flag == ADDITION:
                action = ObjectChangeActionChoices.ACTION_CREATE
            if log_entry.action_flag == CHANGE:
                action = ObjectChangeActionChoices.ACTION_UPDATE
            if log_entry.action_flag == DELETION:
                action = ObjectChangeActionChoices.ACTION_DELETE
            # Unfortunately, we can't get the serialized_object before the change so the calculated Difference
            # will be empty.  So we capture the Django change message to include in object_data to provide some
            # representation of the change
            object_data = serialize_object(custom_field)
            # object_data needs ascii, remove unicode characters from change message
            object_data["changelog_message"] = get_change_message(log_entry).encode("ascii", "ignore").decode()
            object_change = ObjectChange(
                user=log_entry.user,
                action=action,
                changed_object_type=custom_field_type,
                changed_object_id=custom_field.id,
                # Django LogEntry messages don't contain a request id so we make one up
                request_id=uuid.uuid4(),
                object_data=object_data,
            )
            object_change.save()
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
