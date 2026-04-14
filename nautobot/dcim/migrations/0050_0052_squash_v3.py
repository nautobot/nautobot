from django.db import migrations, models
from nautobot.extras.utils import fixup_null_statuses
import nautobot.extras.models.statuses


# From 0050_fix_interface_redundancy_group_association_created

# From 0051_interface_redundancy_group_nullable_status

# From 0052_fix_interface_redundancy_group_created

# From 0051_interface_redundancy_group_nullable_status
def migrate_null_statuses(apps, schema):
    Status = apps.get_model("extras", "Status")
    ContentType = apps.get_model("contenttypes", "ContentType")
    InterfaceRedundancyGroup = apps.get_model("dcim", "interfaceredundancygroup")
    interface_redundancy_group_ct = ContentType.objects.get_for_model(InterfaceRedundancyGroup)
    fixup_null_statuses(
        model=InterfaceRedundancyGroup, model_contenttype=interface_redundancy_group_ct, status_model=Status
    )


def copy_created_to_created_datetimefield(apps, schema):
    InterfaceRedundancyGroupAssociation = apps.get_model("dcim", "interfaceredundancygroupassociation")
    InterfaceRedundancyGroupAssociation.objects.update(created_datetimefield=models.F("created"))


def revert_copy_created_to_created_datetimefield(apps, schema):
    InterfaceRedundancyGroupAssociation = apps.get_model("dcim", "interfaceredundancygroupassociation")
    InterfaceRedundancyGroupAssociation.objects.update(created_datetimefield=None)


class Migration(migrations.Migration):

    replaces = [
        ("dcim", "0050_fix_interface_redundancy_group_association_created"),
        ("dcim", "0051_interface_redundancy_group_nullable_status"),
        ("dcim", "0052_fix_interface_redundancy_group_created"),
    ]

    dependencies = [
        ("dcim", "0022_interface_redundancy_group"),
        ("dcim", "0049_remove_slugs_and_change_device_primary_ip_fields"),
    ]

    operations = [

        # Migration 0022 diverged between 1.6 and 2.0 so we must copy the created field to a new field
        # in order to change it without losing data.
        migrations.AddField(
            model_name="interfaceredundancygroupassociation",
            name="created_datetimefield",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),


        migrations.RunPython(migrate_null_statuses, migrations.RunPython.noop),
        migrations.RunPython(copy_created_to_created_datetimefield, revert_copy_created_to_created_datetimefield),


        migrations.RemoveField(
            model_name="interfaceredundancygroupassociation",
            name="created",
        ),
        migrations.RenameField(
            model_name="interfaceredundancygroupassociation",
            old_name="created_datetimefield",
            new_name="created",
        ),
        # Migration 0022 diverged between 1.6 and 2.0 so we must make the status field nullable here
        # to force Django to recognize that the field has changed.
        migrations.AlterField(
            model_name="interfaceredundancygroup",
            name="status",
            field=nautobot.extras.models.statuses.StatusField(
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="interface_redundancy_groups",
                to="extras.status",
            ),
        ),
        migrations.AlterField(
            model_name="interfaceredundancygroup",
            name="status",
            field=nautobot.extras.models.statuses.StatusField(
                on_delete=models.deletion.PROTECT,
                related_name="interface_redundancy_groups",
                to="extras.status",
            ),
        ),
    ]
