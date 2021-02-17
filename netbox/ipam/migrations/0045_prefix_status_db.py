from django.db import migrations
import django.db.models.deletion
import extras.models.statuses
import extras.management


def populate_prefix_status_db(apps, schema_editor):
    """
    Iterate existing Prefixs and populate `status_db` from `status` field.
    """
    Status = apps.get_model('extras.status')
    Prefix = apps.get_model('ipam.Prefix')
    ContentType = apps.get_model('contenttypes.contenttype')

    content_type = ContentType.objects.get_for_model(Prefix)
    custom_statuses = Status.objects.filter(content_types=content_type)

    for prefix in Prefix.objects.all():
        prefix.status_db = custom_statuses.get(name=prefix.status)
        prefix.save()


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('ipam', '0044_add_custom_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='prefix',
            name='status_db',
            field=extras.models.statuses.StatusField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='prefixs', to='extras.status'),
        ),
        migrations.RunPython(
            extras.management.populate_status_choices,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            populate_prefix_status_db,
            migrations.RunPython.noop,
            hints={'model_name': 'prefix'},
        ),
    ]
