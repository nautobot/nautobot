# Remove legacy GFK fields from CircuitTermination — peers are now resolved via CableTerminationEndpoint.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("circuits", "0022_circuittermination_cloud_network")]
    operations = [
        migrations.RemoveField(model_name="circuittermination", name="_cable_peer_id"),
        migrations.RemoveField(model_name="circuittermination", name="_cable_peer_type"),
    ]
