from django.db import migrations


LOG_LEVEL_MAPPING = {
    "default": "debug",
    "success": "info",
    "failure": "error",
}


def migrate_job_log_entry_log_levels(apps, schema_editor):
    """
    Migrate job log levels from 1.0 values to 2.0 values.
    default => debug
    success => info
    failure => error
    """
    JobLogEntry = apps.get_model("extras", "JobLogEntry")

    for old_log_level, new_log_level in LOG_LEVEL_MAPPING.items():
        JobLogEntry.objects.filter(log_level=old_log_level).update(log_level=new_log_level)


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0089_joblogentry__log_level_default"),
    ]

    operations = [
        migrations.RunPython(
            code=migrate_job_log_entry_log_levels,
            reverse_code=migrations.operations.special.RunPython.noop,
        ),
    ]
