# Data migration: remove orphaned ObjectMetadata rows whose ContentType was deleted while the
# FK was on_delete=SET_NULL. The accompanying schema migration (0145) makes the FK NOT NULL
# with on_delete=CASCADE, so the orphans need to be cleared first.

from django.db import migrations


def delete_orphaned_object_metadata(apps, schema_editor):
    ObjectMetadata = apps.get_model("extras", "ObjectMetadata")
    ObjectMetadata.objects.filter(assigned_object_type__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0143_jobresult_date_terminated_jobresult_revoked_by_and_more"),
    ]

    operations = [
        migrations.RunPython(
            delete_orphaned_object_metadata,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
