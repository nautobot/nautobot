from django.db import migrations
import django.db.models.deletion
import extras.models.statuses
import extras.management


def populate_rack_status_db(apps, schema_editor):
    """
    Iterate existing Racks and populate `status_db` from `status` field.
    """
    Status = apps.get_model('extras.status')
    Rack = apps.get_model('dcim.Rack')
    ContentType = apps.get_model('contenttypes.contenttype')

    content_type = ContentType.objects.get_for_model(Rack)
    custom_statuses = Status.objects.filter(content_types=content_type)

    for rack in Rack.objects.all():
        rack.status_db = custom_statuses.get(name=rack.status)
        rack.save()


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('dcim', '0128_device_add_local_context_data_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='rack',
            name='status_db',
            field=extras.models.statuses.StatusField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='racks', to='extras.status'),
        ),
        migrations.RunPython(
            extras.management.populate_status_choices,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            populate_rack_status_db,
            migrations.RunPython.noop,
            hints={'model_name': 'rack'},
        ),
    ]
