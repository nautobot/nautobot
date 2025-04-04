from django.db import migrations

from nautobot.extras.management import clear_status_choices, populate_status_choices


def populate_controller_status_choices(apps, schema_editor):
    """Create default Status records for the Controller model."""
    populate_status_choices(apps, schema_editor, models=["dcim.Controller"])


def clear_controller_status_choices(apps, schema_editor):
    """Remove default Status records for the Controller model."""
    clear_status_choices(apps, schema_editor, models=["dcim.Controller"])


class Migration(migrations.Migration):
    dependencies = (
        ("contenttypes", "0001_initial"),
        ("extras", "0001_initial_part_1"),
        ("dcim", "0057_controller_models"),
    )

    operations = [
        migrations.RunPython(populate_controller_status_choices, clear_controller_status_choices),
    ]
