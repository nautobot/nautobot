"""Add name, role, status, and tenant fields to VPNTermination."""

from django.db import migrations, models
import django.db.models.deletion

import nautobot.extras.models.roles
import nautobot.extras.models.statuses


class Migration(migrations.Migration):
    """Add name, role, status, and tenant fields to VPNTermination."""

    dependencies = [
        ("extras", "0142_remove_scheduledjob_approval_required"),
        ("tenancy", "0009_update_all_charfields_max_length_to_255"),
        ("vpn", "0004_vpn_overlay_support"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="vpntermination",
            options={
                "ordering": ("name",),
                "verbose_name": "VPN Termination",
                "verbose_name_plural": "VPN Terminations",
            },
        ),
        migrations.AddField(
            model_name="vpntermination",
            name="name",
            field=models.CharField(default="", editable=False, max_length=255),
        ),
        migrations.AddField(
            model_name="vpntermination",
            name="role",
            field=nautobot.extras.models.roles.RoleField(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="extras.role"
            ),
        ),
        migrations.AddField(
            model_name="vpntermination",
            name="status",
            field=nautobot.extras.models.statuses.StatusField(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="extras.status"
            ),
        ),
        migrations.AddField(
            model_name="vpntermination",
            name="tenant",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="vpn_terminations",
                to="tenancy.tenant",
            ),
        ),
    ]
