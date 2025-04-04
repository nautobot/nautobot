from django.db import migrations, models

import nautobot.extras.models.statuses


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0022_interface_redundancy_group"),
        ("dcim", "0051_interface_redundancy_group_nullable_status"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="interfaceredundancygroupassociation",
            name="created",
        ),
        migrations.RenameField(
            model_name="interfaceredundancygroupassociation",
            old_name="created_datetimefield",
            new_name="created",
        ),
        # Migration 0022 diverged between 1.6 and 2.0 so we must make the status field nullable here
        # to force Django to recognize that the field has changed.
        migrations.AlterField(
            model_name="interfaceredundancygroup",
            name="status",
            field=nautobot.extras.models.statuses.StatusField(
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="interface_redundancy_groups",
                to="extras.status",
            ),
        ),
        migrations.AlterField(
            model_name="interfaceredundancygroup",
            name="status",
            field=nautobot.extras.models.statuses.StatusField(
                on_delete=models.deletion.PROTECT,
                related_name="interface_redundancy_groups",
                to="extras.status",
            ),
        ),
    ]
