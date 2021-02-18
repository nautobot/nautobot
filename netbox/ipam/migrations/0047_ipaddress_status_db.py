from django.db import migrations
import django.db.models.deletion
import extras.models.statuses


def populate_ipaddress_status_db(apps, schema_editor):
    """
    Iterate existing IPAddresss and populate `status_db` from `status` field.
    """
    Status = apps.get_model('extras.status')
    IPAddress = apps.get_model('ipam.IPAddress')
    ContentType = apps.get_model('contenttypes.contenttype')

    content_type = ContentType.objects.get_for_model(IPAddress)
    custom_statuses = Status.objects.filter(content_types=content_type)

    for ipaddress in IPAddress.objects.all():
        ipaddress.status_db = custom_statuses.get(slug=ipaddress.status)
        ipaddress.save()


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('ipam', '0046_prefix_status_change_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='ipaddress',
            name='status_db',
            field=extras.models.statuses.StatusField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ipam_ipaddress_related', to='extras.status'),
        ),
        migrations.RunPython(
            populate_ipaddress_status_db,
            migrations.RunPython.noop,
            hints={'model_name': 'ipaddress'},
        ),
    ]
