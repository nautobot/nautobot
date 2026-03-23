# Add connector/position to CablePath for per-lane breakout paths.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("dcim", "0089_remove_cable_old_gfk_fields")]
    operations = [
        migrations.AddField(
            model_name="cablepath", name="connector", field=models.PositiveSmallIntegerField(blank=True, null=True)
        ),
        migrations.AddField(
            model_name="cablepath", name="position", field=models.PositiveSmallIntegerField(blank=True, null=True)
        ),
        migrations.AlterUniqueTogether(
            name="cablepath", unique_together={("origin_type", "origin_id", "connector", "position")}
        ),
    ]
