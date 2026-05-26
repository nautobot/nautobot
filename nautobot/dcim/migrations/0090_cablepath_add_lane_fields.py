# Add `peer_connector` to CablePath for per-peer-connector breakout paths, and drop the denormalized
# `_path` FK from PathEndpoint subclasses (replaced by a GenericRelation `cable_paths` resolving
# through CablePath.origin — see circuits/0023 for the CircuitTermination counterpart).
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("dcim", "0089_remove_cable_old_gfk_fields")]
    operations = [
        migrations.AddField(
            model_name="cablepath",
            name="peer_connector",
            field=models.PositiveSmallIntegerField(
                default=1,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(16),  # CABLE_BREAKOUT_MAX_CONNECTORS
                ],
            ),
        ),
        migrations.AlterUniqueTogether(
            name="cablepath", unique_together={("origin_type", "origin_id", "peer_connector")}
        ),
        migrations.AlterModelOptions(name="cablepath", options={"ordering": ["peer_connector"]}),
        migrations.RemoveField(model_name="consoleport", name="_path"),
        migrations.RemoveField(model_name="consoleserverport", name="_path"),
        migrations.RemoveField(model_name="powerport", name="_path"),
        migrations.RemoveField(model_name="poweroutlet", name="_path"),
        migrations.RemoveField(model_name="interface", name="_path"),
        migrations.RemoveField(model_name="powerfeed", name="_path"),
    ]
