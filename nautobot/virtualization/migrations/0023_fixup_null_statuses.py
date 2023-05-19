from django.db import migrations

from nautobot.extras.utils import fixup_null_statuses


def migrate_null_statuses(apps, schema):
    status_model = apps.get_model("extras", "Status")
    for model_name in (
        "VirtualMachine",
        "VMInterface",
    ):
        model = apps.get_model("virtualization", model_name)
        fixup_null_statuses(model=model, status_model=status_model)


class Migration(migrations.Migration):
    dependencies = [
        ("virtualization", "0022_vminterface_timestamps_data_migration"),
    ]

    operations = [
        migrations.RunPython(migrate_null_statuses, migrations.RunPython.noop),
    ]
