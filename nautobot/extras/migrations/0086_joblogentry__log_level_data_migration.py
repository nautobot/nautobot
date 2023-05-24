from django.db import migrations


LOG_LEVEL_MAPPING = {
    "default": "info",
    "success": "info",
    "failure": "error",
}


def migrate_job_log_entry_log_levels(apps, schema_editor):
    """
    Migrate job log levels from 1.0 values to 2.0 values.
    default => info
    success => info
    failure => error
    """
    JobLogEntry = apps.get_model("extras", "JobLogEntry")

    for entry in JobLogEntry.objects.all():
        if entry.log_level in LOG_LEVEL_MAPPING:
            entry.log_level = LOG_LEVEL_MAPPING[entry.log_level]
            entry.save()


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0085_jobresult__log_level_default"),
    ]

    operations = [
        migrations.RunPython(
            code=migrate_job_log_entry_log_levels,
            reverse_code=migrations.operations.special.RunPython.noop,
        ),
    ]
