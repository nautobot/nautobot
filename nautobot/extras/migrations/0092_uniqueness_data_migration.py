from django.db import migrations

from nautobot.core.utils.migrations import check_for_duplicates_with_natural_key_fields_in_migration


def ensure_unique_scheduledjob_names(apps, schema_editor):
    ScheduledJob = apps.get_model("extras", "ScheduledJob")

    cache = set()
    for instance in ScheduledJob.objects.all():
        name = instance.name
        counter = 1
        while name in cache:
            suffix = f" {counter}"
            max_name_length = 200 - len(suffix)
            name = f"{instance.name[:max_name_length]}{suffix}"
            counter += 1

        if name != instance.name:
            print(f'    Scheduled Job instance {instance.id} is being renamed to "{name}" for uniqueness')
            instance.name = name
            instance.save()

        cache.add(name)


def check_for_duplicates(apps, schema_editor):
    ConfigContext = apps.get_model("extras", "ConfigContext")
    ConfigContextSchema = apps.get_model("extras", "ConfigContextSchema")
    ExportTemplate = apps.get_model("extras", "ExportTemplate")

    check_for_duplicates_with_natural_key_fields_in_migration(ConfigContext, ["name"])
    check_for_duplicates_with_natural_key_fields_in_migration(ConfigContextSchema, ["name"])
    check_for_duplicates_with_natural_key_fields_in_migration(ExportTemplate, ["name"])


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0091_scheduledjob__data_migration"),
    ]

    operations = [
        migrations.RunPython(ensure_unique_scheduledjob_names, migrations.RunPython.noop),
        migrations.RunPython(check_for_duplicates, migrations.RunPython.noop),
    ]
