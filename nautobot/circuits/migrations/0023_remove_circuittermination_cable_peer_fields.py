# Remove legacy denormalized fields from CircuitTermination — peers are now resolved via
# CableToCableTermination, the cached `cable` FK is replaced with a property derived from the join
# model's reverse `cable_termination` accessor, and `_path` is replaced with a GenericRelation
# (`cable_paths`) on PathEndpoint that resolves through CablePath.origin.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("circuits", "0022_circuittermination_cloud_network")]
    operations = [
        migrations.RemoveField(model_name="circuittermination", name="_cable_peer_id"),
        migrations.RemoveField(model_name="circuittermination", name="_cable_peer_type"),
        migrations.RemoveField(model_name="circuittermination", name="cable"),
        migrations.RemoveField(model_name="circuittermination", name="_path"),
    ]
