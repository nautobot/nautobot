from django.db import migrations
import django.db.models.deletion
import extras.models.statuses
import extras.management


def populate_cable_status_db(apps, schema_editor):
    """
    Iterate existing Cables and populate `status_db` from `status` field.
    """
    Status = apps.get_model('extras.status')
    Cable = apps.get_model('dcim.Cable')
    ContentType = apps.get_model('contenttypes.contenttype')

    content_type = ContentType.objects.get_for_model(Cable)
    custom_statuses = Status.objects.filter(content_types=content_type)

    for cable in Cable.objects.all():
        cable.status_db = custom_statuses.get(name=cable.status)
        cable.save()


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('dcim', '0130_rack_status_change_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='cable',
            name='status_db',
            field=extras.models.statuses.StatusField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='cables', to='extras.status'),
        ),
        migrations.RunPython(
            extras.management.populate_status_choices,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            populate_cable_status_db,
            migrations.RunPython.noop,
            hints={'model_name': 'cable'},
        ),
    ]
