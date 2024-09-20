from django.db import migrations

from nautobot.core.choices import ColorChoices
from nautobot.extras.utils import fixup_null_statuses


def fixup_null_roles(apps, schema):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Device = apps.get_model("dcim", "Device")
    device_ct = ContentType.objects.get_for_model(Device)
    Role = apps.get_model("extras", "Role")
    instances_to_fixup = Device.objects.filter(role__isnull=True)
    if instances_to_fixup.exists():
        null_role, _ = Role.objects.get_or_create(
            name="NULL",
            defaults={
                "color": ColorChoices.COLOR_BLACK,
                "description": "Created by Nautobot to replace invalid null references",
            },
        )
        null_role.content_types.add(device_ct)
        updated_count = instances_to_fixup.update(role=null_role)
        print(f"    Found and fixed {updated_count} instances of Device that had null 'role' field.")


def migrate_null_statuses(apps, schema):
    status_model = apps.get_model("extras", "Status")
    ContentType = apps.get_model("contenttypes", "ContentType")
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
        model_ct = ContentType.objects.get_for_model(model)
        fixup_null_statuses(model=model, model_contenttype=model_ct, status_model=status_model)


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("dcim", "0045_ipam__namespaces"),
        ("extras", "0061_role_and_alter_status"),
    ]

    operations = [
        migrations.RunPython(migrate_null_statuses, migrations.RunPython.noop),
        migrations.RunPython(fixup_null_roles, migrations.RunPython.noop),
    ]
