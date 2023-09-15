from django.db import migrations


def zero_out_vminterface_timestamps(apps, schema_editor):
    """Set initial created/last_updated fields of existing VMInterfaces to None, rather than the time of migration."""
    VMInterface = apps.get_model("virtualization.vminterface")
    VMInterface.objects.all().update(created=None, last_updated=None)


class Migration(migrations.Migration):
    dependencies = [
        ("virtualization", "0021_tagsfield_and_vminterface_to_primarymodel"),
    ]

    operations = [
        migrations.RunPython(zero_out_vminterface_timestamps, migrations.RunPython.noop),
    ]
