# Generated by Django 4.2.15 on 2024-08-26 17:20

from django.db import migrations
import django.db.models.deletion

import nautobot.extras.models.statuses


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0114_computedfield_grouping"),
        ("ipam", "0047_alter_ipaddress_role_alter_ipaddress_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="vrf",
            name="status",
            field=nautobot.extras.models.statuses.StatusField(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="extras.status"
            ),
        ),
    ]