from django.db import migrations

from nautobot.extras.management import clear_status_choices, populate_status_choices


def populate_software_status_choices(apps, schema_editor):
    """Create default Status records for the SoftwareImageFile and SoftwareVersion models."""
    populate_status_choices(apps, schema_editor, models=["dcim.SoftwareImageFile", "dcim.SoftwareVersion"])


def clear_software_status_choices(apps, schema_editor):
    """Remove default Status records for the SoftwareImageFile and SoftwareVersion models."""
    clear_status_choices(apps, schema_editor, models=["dcim.SoftwareImageFile", "dcim.SoftwareVersion"])


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0001_initial"),
        ("extras", "0001_initial_part_1"),
        ("dcim", "0054_softwareimage_softwareversion"),
    ]

    operations = [
        migrations.RunPython(populate_software_status_choices, clear_software_status_choices),
    ]
