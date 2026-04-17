"""Backfill VPNTermination.name and populate default status choices for VPNTermination."""

from django.db import migrations

import nautobot.extras.management


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
    """Backfill VPNTermination.name and populate default status choices for VPNTermination."""

    dependencies = [
        ("vpn", "0005_vpntermination_enhancements"),
    ]

    operations = [
        migrations.RunPython(
            populate_vpntermination_names,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            code=populate_vpntermination_status_choices,
            reverse_code=clear_vpntermination_status_choices,
        ),
    ]
