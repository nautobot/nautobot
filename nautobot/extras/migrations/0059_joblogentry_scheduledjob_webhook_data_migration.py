from django.db import migrations


def null_joblogentry_fields_to_empty(apps, schema_editor):
    """Change null absolute_url and log_object fields to empty strings instead."""
    JobLogEntry = apps.get_model("extras.joblogentry")
    JobLogEntry.objects.filter(log_object__isnull=True).update(log_object="")
    JobLogEntry.objects.filter(absolute_url__isnull=True).update(absolute_url="")


def null_scheduledjob_fields_to_empty(apps, schema_editor):
    """Change null queue field to empty string instead."""
    ScheduledJob = apps.get_model("extras.scheduledjob")
    ScheduledJob.objects.filter(queue__isnull=True).update(queue="")


def null_webhook_fields_to_empty(apps, schema_editor):
    """Change null ca_file_path field to empty string instead."""
    WebHook = apps.get_model("extras.webhook")
    WebHook.objects.filter(ca_file_path__isnull=True).update(ca_file_path="")


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0058_jobresult_add_time_status_idxs"),
    ]

    operations = [
        migrations.RunPython(null_joblogentry_fields_to_empty, migrations.RunPython.noop),
        migrations.RunPython(null_scheduledjob_fields_to_empty, migrations.RunPython.noop),
        migrations.RunPython(null_webhook_fields_to_empty, migrations.RunPython.noop),
    ]
