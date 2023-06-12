from django.db import migrations


def null_macaddress_to_empty(apps, schema_editor):
    """Change null mac_address values to empty strings instead."""
    VMInterface = apps.get_model("virtualization.vminterface")
    VMInterface.objects.filter(mac_address__isnull=True).update(mac_address="")


class Migration(migrations.Migration):
    dependencies = [
        ("virtualization", "0009_cluster_location"),
    ]

    operations = [
        migrations.RunPython(null_macaddress_to_empty, migrations.RunPython.noop),
    ]
