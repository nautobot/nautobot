from django.db import migrations, models

from nautobot.extras.utils import fixup_null_statuses


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
    dependencies = [
        ("dcim", "0022_interface_redundancy_group"),
        ("dcim", "0050_fix_interface_redundancy_group_association_created"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0001_initial_part_1"),
    ]

    operations = [
        migrations.RunPython(migrate_null_statuses, migrations.RunPython.noop),
        migrations.RunPython(copy_created_to_created_datetimefield, revert_copy_created_to_created_datetimefield),
    ]
