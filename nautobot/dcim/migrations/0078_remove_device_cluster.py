from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0077_device_cluster_to_clusters_data_migration"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="device",
            name="cluster",
        ),
    ]
