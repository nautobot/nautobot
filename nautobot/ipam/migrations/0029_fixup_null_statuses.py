from django.db import migrations

from nautobot.extras.utils import fixup_null_statuses


def migrate_null_statuses(apps, schema):
    status_model = apps.get_model("extras", "Status")
    for model_name in (
        "IPAddress",
        "Prefix",
        "VLAN",
    ):
        model = apps.get_model("ipam", model_name)
        fixup_null_statuses(model=model, status_model=status_model)


class Migration(migrations.Migration):
    dependencies = [
        ("ipam", "0028_tagsfield"),
    ]

    operations = [
        migrations.RunPython(migrate_null_statuses, migrations.RunPython.noop),
    ]
