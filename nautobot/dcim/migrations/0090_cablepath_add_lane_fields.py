# Add far-side `connector` to CablePath for per-connector breakout paths, and drop the denormalized
# `_path` FK from PathEndpoint subclasses (replaced by a GenericRelation `cable_paths` resolving
# through CablePath.origin — see circuits/0023 for the CircuitTermination counterpart).
from django.db import migrations, models
import django.db.models.expressions


class Migration(migrations.Migration):
    dependencies = [("dcim", "0089_remove_cable_old_gfk_fields")]
    operations = [
        migrations.AddField(
            model_name="cablepath", name="connector", field=models.PositiveSmallIntegerField(blank=True, null=True)
        ),
        migrations.AlterUniqueTogether(name="cablepath", unique_together={("origin_type", "origin_id", "connector")}),
        migrations.AlterModelOptions(
            name="cablepath",
            options={
                "ordering": [
                    django.db.models.expressions.OrderBy(django.db.models.expressions.F("connector"), nulls_first=True),
                ]
            },
        ),
        migrations.RemoveField(model_name="consoleport", name="_path"),
        migrations.RemoveField(model_name="consoleserverport", name="_path"),
        migrations.RemoveField(model_name="powerport", name="_path"),
        migrations.RemoveField(model_name="poweroutlet", name="_path"),
        migrations.RemoveField(model_name="interface", name="_path"),
        migrations.RemoveField(model_name="powerfeed", name="_path"),
    ]
