"""Populate default CableType records for common cable configurations."""

from django.db import migrations

from nautobot.dcim.utils import clear_default_cable_types, populate_default_cable_types


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0085_cabletype"),
    ]

    operations = [
        migrations.RunPython(populate_default_cable_types, clear_default_cable_types),
    ]
