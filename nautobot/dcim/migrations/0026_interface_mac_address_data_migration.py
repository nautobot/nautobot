from django.db import migrations


def null_macaddress_to_empty(apps, schema_editor):
    """Change null mac_address values to empty strings instead."""
    Interface = apps.get_model("dcim.interface")
    Interface.objects.filter(mac_address__isnull=True).update(mac_address="")


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0025_mptt_to_tree_queries"),
    ]

    operations = [
        migrations.RunPython(null_macaddress_to_empty, migrations.RunPython.noop),
    ]
