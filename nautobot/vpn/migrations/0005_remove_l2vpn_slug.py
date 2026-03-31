from django.db import migrations


class Migration(migrations.Migration):
    """No-op migration kept for migration chain integrity after the VPN overlay refactor."""

    dependencies = [
        ('vpn', '0004_l2vpntermination_primary_model'),
    ]

    operations = []
