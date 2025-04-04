from django.db import migrations

from nautobot.extras.management import clear_status_choices, populate_status_choices


def populate_module_status_choices(apps, schema_editor):
    """Create default Status records for the Module model."""
    populate_status_choices(apps, schema_editor, models=["dcim.Module"])


def clear_module_status_choices(apps, schema_editor):
    """Remove default Status records for the Module model."""
    clear_status_choices(apps, schema_editor, models=["dcim.Module"])


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0001_initial"),
        ("extras", "0001_initial_part_1"),
        ("dcim", "0061_module_models"),
    ]

    operations = [
        migrations.RunPython(populate_module_status_choices, clear_module_status_choices),
    ]
