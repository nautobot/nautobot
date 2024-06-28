from django.db import migrations

from nautobot.extras.choices import DynamicGroupTypeChoices


def set_dynamic_group_group_types(apps, schema_editor):
    """Set dynamic group group_type values appropriately."""
    DynamicGroup = apps.get_model("extras", "DynamicGroup")

    # The group_type field defaults to TYPE_DYNAMIC_FILTER
    # There are no preexisting TYPE_STATIC groups as that's a new feature
    # Any group that has children should be converted to TYPE_DYNAMIC_SET
    DynamicGroup.objects.filter(children__isnull=False).distinct().update(
        group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET
    )


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0111_metadatatype_metadatachoice"),
    ]

    operations = [
        migrations.RunPython(
            code=set_dynamic_group_group_types,
            reverse_code=migrations.operations.special.RunPython.noop,
        ),
    ]
