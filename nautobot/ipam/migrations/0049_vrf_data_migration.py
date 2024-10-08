# Generated by Django 4.2.15 on 2024-08-26 18:05

from django.db import migrations

from nautobot.extras.management import clear_status_choices, populate_status_choices


def populate_vrf_status_choices(apps, schema_editor):
    """Create default Status records for the VRF model."""
    populate_status_choices(apps, schema_editor, models=["ipam.VRF"])


def clear_vrf_status_choices(apps, schema_editor):
    """Remove default Status records for the VRF model."""
    clear_status_choices(apps, schema_editor, models=["ipam.VRF"])


class Migration(migrations.Migration):
    dependencies = [
        ("ipam", "0048_vrf_status"),
    ]

    operations = [
        migrations.RunPython(populate_vrf_status_choices, clear_vrf_status_choices),
    ]
