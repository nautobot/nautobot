from django.db import migrations
import django.db.models.deletion
import nautobot.extras.models.statuses


def populate_vlan_status_db(apps, schema_editor):
    """
    Iterate existing VLANs and populate `status_db` from `status` field.
    """
    Status = apps.get_model('extras.status')
    VLAN = apps.get_model('ipam.VLAN')
    ContentType = apps.get_model('contenttypes.contenttype')

    content_type = ContentType.objects.get_for_model(VLAN)
    custom_statuses = Status.objects.filter(content_types=content_type)

    for vlan in VLAN.objects.all():
        vlan.status_db = custom_statuses.get(slug=vlan.status)
        vlan.save()


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('ipam', '0048_ipaddress_status_change_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='vlan',
            name='status_db',
            field=nautobot.extras.models.statuses.StatusField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ipam_vlan_related', to='extras.status'),
        ),
        migrations.RunPython(
            populate_vlan_status_db,
            migrations.RunPython.noop,
            hints={'model_name': 'vlan'},
        ),
    ]
