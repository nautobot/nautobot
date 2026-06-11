from django.db import migrations

from nautobot.extras.management import (
    clear_role_choices,
    clear_status_choices,
    populate_role_choices,
    populate_status_choices,
)


def populate_default_status_and_role_choices_for_ip_range(apps, schema_editor):
    """Create/link default Status and Role records for the IPRange content-type."""
    populate_status_choices(apps, schema_editor, models=["ipam.IPRange"])
    populate_role_choices(apps, schema_editor, models=["ipam.IPRange"])


def clear_default_status_and_role_choices_for_ip_range(apps, schema_editor):
    """De-link/delete all Status and Role records from the IPRange content-type."""
    clear_status_choices(apps, schema_editor, models=["ipam.IPRange"])
    clear_role_choices(apps, schema_editor, models=["ipam.IPRange"])


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0001_initial"),
        ("ipam", "0057_iprange"),
    ]

    operations = [
        migrations.RunPython(
            populate_default_status_and_role_choices_for_ip_range,
            clear_default_status_and_role_choices_for_ip_range,
        ),
    ]
