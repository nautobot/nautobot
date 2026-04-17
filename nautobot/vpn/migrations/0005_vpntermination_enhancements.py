"""Add name, role, status, and tenant fields to VPNTermination and populate default status choices."""

from django.db import migrations, models
import django.db.models.deletion

import nautobot.extras.management
import nautobot.extras.models.roles
import nautobot.extras.models.statuses


def populate_vpntermination_names(apps, schema_editor):
    """Backfill the name field for existing VPNTermination rows."""
    VPNTermination = apps.get_model("vpn", "VPNTermination")
    for termination in VPNTermination.objects.select_related(
        "vlan", "vlan__vlan_group", "interface", "interface__device", "vm_interface", "vm_interface__virtual_machine"
    ).all():
        if termination.interface:
            parent = termination.interface.device
            obj = termination.interface
        elif termination.vm_interface:
            parent = termination.vm_interface.virtual_machine
            obj = termination.vm_interface
        elif termination.vlan:
            parent = termination.vlan.vlan_group
            obj = termination.vlan
        else:
            parent = None
            obj = None

        if parent:
            termination.name = f"{parent.name} {obj.name}"
        else:
            termination.name = str(obj.name if obj else "")
        termination.save(update_fields=["name"])


def populate_vpntermination_status_choices(apps, schema_editor):
    """Link default Status records to the VPNTermination content-type."""
    nautobot.extras.management.populate_status_choices(apps, schema_editor, models=["vpn.VPNTermination"])


def clear_vpntermination_status_choices(apps, schema_editor):
    """De-link all Status records from the VPNTermination content-type."""
    nautobot.extras.management.clear_status_choices(apps, schema_editor, models=["vpn.VPNTermination"])


class Migration(migrations.Migration):
    """Add name, role, status, and tenant fields to VPNTermination."""

    dependencies = [
        ("extras", "0142_remove_scheduledjob_approval_required"),
        ("tenancy", "0009_update_all_charfields_max_length_to_255"),
        ("vpn", "0004_vpn_overlay_support"),
    ]

    operations = [
        # Update model options (ordering by name)
        migrations.AlterModelOptions(
            name="vpntermination",
            options={
                "ordering": ("name",),
                "verbose_name": "VPN Termination",
                "verbose_name_plural": "VPN Terminations",
            },
        ),
        # Add name field with empty default for existing rows
        migrations.AddField(
            model_name="vpntermination",
            name="name",
            field=models.CharField(default="", editable=False, max_length=255),
        ),
        # Backfill name for existing rows
        migrations.RunPython(
            populate_vpntermination_names,
            migrations.RunPython.noop,
        ),
        # Add role field
        migrations.AddField(
            model_name="vpntermination",
            name="role",
            field=nautobot.extras.models.roles.RoleField(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="extras.role"
            ),
        ),
        # Add status field
        migrations.AddField(
            model_name="vpntermination",
            name="status",
            field=nautobot.extras.models.statuses.StatusField(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="extras.status"
            ),
        ),
        # Add tenant field
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
        # Populate default status choices for VPNTermination
        migrations.RunPython(
            code=populate_vpntermination_status_choices,
            reverse_code=clear_vpntermination_status_choices,
        ),
    ]
