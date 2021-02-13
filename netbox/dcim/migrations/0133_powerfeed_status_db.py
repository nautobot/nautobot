from django.db import migrations
import django.db.models.deletion
import extras.models.statuses
import extras.management


def populate_powerfeed_status_db(apps, schema_editor):
    """
    Iterate existing PowerFeeds and populate `status_db` from `status` field.
    """
    Status = apps.get_model('extras.status')
    PowerFeed = apps.get_model('dcim.PowerFeed')
    ContentType = apps.get_model('contenttypes.contenttype')

    content_type = ContentType.objects.get_for_model(PowerFeed)
    custom_statuses = Status.objects.filter(content_types=content_type)

    for powerfeed in PowerFeed.objects.all():
        powerfeed.status_db = custom_statuses.get(name=powerfeed.status)
        powerfeed.save()


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('dcim', '0132_cable_status_change_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='powerfeed',
            name='status_db',
            field=extras.models.statuses.StatusField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='powerfeeds', to='extras.status'),
        ),
        migrations.RunPython(
            extras.management.populate_status_choices,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            populate_powerfeed_status_db,
            migrations.RunPython.noop,
            hints={'model_name': 'powerfeed'},
        ),
    ]
