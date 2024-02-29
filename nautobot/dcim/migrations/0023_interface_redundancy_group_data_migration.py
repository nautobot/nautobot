from django.db import migrations

from nautobot.extras.management import clear_metadata_choices, populate_metadata_choices


def populate_interface_redundancy_group_status(apps, schema_editor):
    """Create/link default Status records for the InterfaceRedundancyGroup content-type."""
    populate_metadata_choices(apps, schema_editor, models=["dcim.InterfaceRedundancyGroup"])


def clear_interface_redundancy_group_status(apps, schema_editor):
    """De-link/delete all Status records from the InterfaceRedundancyGroup content-type."""
    clear_metadata_choices(apps, schema_editor, models=["dcim.InterfaceRedundancyGroup"])


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0022_interface_redundancy_group"),
    ]

    operations = [
        migrations.RunPython(populate_interface_redundancy_group_status, clear_interface_redundancy_group_status),
    ]
