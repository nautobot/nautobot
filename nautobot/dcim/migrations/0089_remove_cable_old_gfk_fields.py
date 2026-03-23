# Remove old GFK fields from Cable (data migrated to CableTerminationEndpoint).
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("dcim", "0088_populate_cableterminationendpoint")]
    operations = [
        migrations.RemoveField(model_name="cable", name="_termination_a_device"),
        migrations.RemoveField(model_name="cable", name="_termination_b_device"),
        migrations.RemoveField(model_name="cable", name="termination_a_id"),
        migrations.RemoveField(model_name="cable", name="termination_a_type"),
        migrations.RemoveField(model_name="cable", name="termination_b_id"),
        migrations.RemoveField(model_name="cable", name="termination_b_type"),
    ]
