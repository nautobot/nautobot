import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0075_interface_duplex_interface_speed_and_more"),
        ("virtualization", "0030_alter_virtualmachine_local_config_context_data_owner_content_type_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeviceClusterAssignment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                (
                    "cluster",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="device_assignments",
                        to="virtualization.cluster",
                    ),
                ),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cluster_assignments",
                        to="dcim.device",
                    ),
                ),
            ],
            options={
                "ordering": ["device", "cluster"],
                "unique_together": {("device", "cluster")},
            },
        ),
        migrations.AddField(
            model_name="device",
            name="clusters",
            field=models.ManyToManyField(
                blank=True, related_name="devices", through="dcim.DeviceClusterAssignment", to="virtualization.cluster"
            ),
        ),
    ]
