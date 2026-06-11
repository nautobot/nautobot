# Schema migration: switch ObjectMetadata.assigned_object_type from on_delete=SET_NULL+null=True
# to on_delete=CASCADE+NOT NULL. Orphaned rows are removed by 0144 (data migration) so the
# NOT NULL constraint can be applied cleanly.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0144_delete_orphaned_object_metadata"),
    ]

    operations = [
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
