# Remove legacy GFK fields from CircuitTermination — peers are now resolved via CableToCableTermination,
# and the cached `cable` FK is replaced with a property derived from the join model's reverse
# `cable_termination` accessor.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("circuits", "0022_circuittermination_cloud_network")]
    operations = [
        migrations.RemoveField(model_name="circuittermination", name="_cable_peer_id"),
        migrations.RemoveField(model_name="circuittermination", name="_cable_peer_type"),
        migrations.RemoveField(model_name="circuittermination", name="cable"),
    ]
