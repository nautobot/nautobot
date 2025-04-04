from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0022_interface_redundancy_group"),
        ("dcim", "0049_remove_slugs_and_change_device_primary_ip_fields"),
    ]

    operations = [
        # Migration 0022 diverged between 1.6 and 2.0 so we must copy the created field to a new field
        # in order to change it without losing data.
        migrations.AddField(
            model_name="interfaceredundancygroupassociation",
            name="created_datetimefield",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
