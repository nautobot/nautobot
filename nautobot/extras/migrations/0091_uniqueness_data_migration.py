from django.db import migrations, models
import sys


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

    failed = False

    dupe_cc = ConfigContext.objects.values("name").order_by().annotate(count=models.Count("name")).filter(count__gt=1)
    if dupe_cc.exists():
        failed = True
        print(
            f"    Duplicate ConfigContext names detected: {list(dupe_cc.values_list('name', flat=True))}",
            file=sys.stderr,
        )

    dupe_ccs = (
        ConfigContextSchema.objects.values("name").order_by().annotate(count=models.Count("name")).filter(count__gt=1)
    )
    if dupe_ccs.exists():
        failed = True
        print(
            f"    Duplicate ConfigContextSchema names detected: {list(dupe_ccs.values_list('name', flat=True))}",
            file=sys.stderr,
        )

    dupe_et = ExportTemplate.objects.values("name").order_by().annotate(count=models.Count("name")).filter(count__gt=1)
    if dupe_et.exists():
        failed = True
        print(
            f"    Duplicate ExportTemplate names detected: {list(dupe_et.values_list('name', flat=True))}",
            file=sys.stderr,
        )

    if failed:
        print(
            "    Unable to proceed with migrations; in Nautobot 2.0+ the name for these records must be unique.",
            file=sys.stderr,
        )
        raise RuntimeError("Duplicate record names must be manually resolved before migrating.")


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0090_scheduledjob__data_migration"),
    ]

    operations = [
        migrations.RunPython(ensure_unique_scheduledjob_names, migrations.RunPython.noop),
        migrations.RunPython(check_for_duplicates, migrations.RunPython.noop),
    ]
