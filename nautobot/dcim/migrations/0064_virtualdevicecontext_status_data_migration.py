from django.db import migrations

from nautobot.extras.management import clear_status_choices, populate_status_choices


def populate_virtual_device_context_status(apps, schema_editor):
    """
    Create default Status records for the VirtualDeviceContext content-type.
    """
    # Create VirtualDeviceContext Statuses and add dcim.VirtualDeviceContext to its content_types
    populate_status_choices(apps, schema_editor, models=["dcim.VirtualDeviceContext"])


def clear_virtual_device_context_status(apps, schema_editor):
    """
    De-link/delete all Status records from the VirtualDeviceContext content-type.
    """
    clear_status_choices(apps, schema_editor, models=["dcim.VirtualDeviceContext"])


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0063_interfacevdcassignment_virtualdevicecontext_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_virtual_device_context_status, clear_virtual_device_context_status),
    ]
