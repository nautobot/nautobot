# Generated for ObjectMetadata.assigned_object_type FK semantics change.
#
# Glenn Matthews suggested switching from on_delete=SET_NULL to on_delete=CASCADE — there's no
# realistic scenario in which we'd delete a ContentType but want the ObjectMetadata for that
# model to stick around. Any pre-existing orphaned rows (assigned_object_type=NULL from the
# prior SET_NULL behavior) are deleted in a data migration before the schema change so the
# NOT NULL constraint can be applied.

from django.db import migrations, models
import django.db.models.deletion


def delete_orphaned_object_metadata(apps, schema_editor):
    ObjectMetadata = apps.get_model("extras", "ObjectMetadata")
    ObjectMetadata.objects.filter(assigned_object_type__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0143_jobresult_date_terminated_jobresult_revoked_by_and_more"),
    ]

    operations = [
        migrations.RunPython(
            delete_orphaned_object_metadata,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="objectmetadata",
            name="assigned_object_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="contenttypes.contenttype",
            ),
        ),
    ]
