from django.db import migrations

from nautobot.extras.utils import fixup_null_statuses


def migrate_null_statuses(apps, schema):
    status_model = apps.get_model("extras", "Status")
    ContentType = apps.get_model("contenttypes", "ContentType")
    for model_name in (
        "VirtualMachine",
        "VMInterface",
    ):
        model = apps.get_model("virtualization", model_name)
        model_ct = ContentType.objects.get_for_model(model)
        fixup_null_statuses(model=model, model_contenttype=model_ct, status_model=status_model)


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0001_initial_part_1"),
        ("virtualization", "0023_ipam__namespaces"),
    ]

    operations = [
        migrations.RunPython(migrate_null_statuses, migrations.RunPython.noop),
    ]
