# Remove legacy GFK fields from Cable (data migrated to CableToCableTermination) and from
# CableTermination subclasses (peers are now resolved via CableToCableTermination).
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("dcim", "0088_populate_cabletocabletermination")]
    operations = [
        migrations.RemoveField(model_name="cable", name="_termination_a_device"),
        migrations.RemoveField(model_name="cable", name="_termination_b_device"),
        migrations.RemoveField(model_name="cable", name="termination_a_id"),
        migrations.RemoveField(model_name="cable", name="termination_a_type"),
        migrations.RemoveField(model_name="cable", name="termination_b_id"),
        migrations.RemoveField(model_name="cable", name="termination_b_type"),
        migrations.RemoveField(model_name="consoleport", name="_cable_peer_id"),
        migrations.RemoveField(model_name="consoleport", name="_cable_peer_type"),
        migrations.RemoveField(model_name="consoleserverport", name="_cable_peer_id"),
        migrations.RemoveField(model_name="consoleserverport", name="_cable_peer_type"),
        migrations.RemoveField(model_name="frontport", name="_cable_peer_id"),
        migrations.RemoveField(model_name="frontport", name="_cable_peer_type"),
        migrations.RemoveField(model_name="interface", name="_cable_peer_id"),
        migrations.RemoveField(model_name="interface", name="_cable_peer_type"),
        migrations.RemoveField(model_name="powerfeed", name="_cable_peer_id"),
        migrations.RemoveField(model_name="powerfeed", name="_cable_peer_type"),
        migrations.RemoveField(model_name="poweroutlet", name="_cable_peer_id"),
        migrations.RemoveField(model_name="poweroutlet", name="_cable_peer_type"),
        migrations.RemoveField(model_name="powerport", name="_cable_peer_id"),
        migrations.RemoveField(model_name="powerport", name="_cable_peer_type"),
        migrations.RemoveField(model_name="rearport", name="_cable_peer_id"),
        migrations.RemoveField(model_name="rearport", name="_cable_peer_type"),
    ]
