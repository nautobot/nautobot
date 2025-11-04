from django.db import migrations


def migrate_device_cluster_assignments(apps, schema_editor):
    """
    Migrate existing device cluster assignments from the old ForeignKey field
    to the new many-to-many relationship through DeviceClusterAssignment.
    """
    Device = apps.get_model("dcim", "Device")
    DeviceClusterAssignment = apps.get_model("dcim", "DeviceClusterAssignment")
    devices_with_clusters = Device.objects.filter(cluster__isnull=False).select_related("cluster")
    assignments_to_create = []
    for device in devices_with_clusters:
        assignments_to_create.append(DeviceClusterAssignment(device=device, cluster=device.cluster))
    if assignments_to_create:
        DeviceClusterAssignment.objects.bulk_create(assignments_to_create, batch_size=1000)


def reverse_migrate_device_cluster_assignments(apps, schema_editor):
    """
    Reverse migration - restore the cluster field from DeviceClusterAssignment records.
    Note: This can only restore one cluster per device if multiple exist.
    """
    DeviceClusterAssignment = apps.get_model("dcim", "DeviceClusterAssignment")

    # For each device, get the first cluster assignment and set it as the device's cluster
    for assignment in DeviceClusterAssignment.objects.select_related("device", "cluster"):
        if not assignment.device.cluster:
            assignment.device.cluster = assignment.cluster
            assignment.device.save(update_fields=["cluster"])


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0076_add_deviceclusterassignment"),
    ]

    operations = [
        migrations.RunPython(migrate_device_cluster_assignments, reverse_migrate_device_cluster_assignments),
    ]
