from django.db import migrations

from nautobot.extras.utils import fixup_null_statuses


def migrate_null_statuses(apps, schema):
    status_model = apps.get_model("extras", "Status")
    for model_name in (
        "Cable",
        "Device",
        "DeviceRedundancyGroup",
        "Interface",
        "Location",
        "PowerFeed",
        "Rack",
    ):
        model = apps.get_model("dcim", model_name)
        fixup_null_statuses(model=model, status_model=status_model)


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0040_tagsfield"),
    ]

    operations = [
        migrations.RunPython(migrate_null_statuses, migrations.RunPython.noop),
    ]
