from django.db import migrations
import django.db.models.deletion
import extras.models.statuses
import extras.management


def populate_virtualmachine_status_db(apps, schema_editor):
    """
    Iterate existing VirtualMachines and populate `status_db` from `status` field.
    """
    Status = apps.get_model('extras.status')
    VirtualMachine = apps.get_model('virtualization.VirtualMachine')
    ContentType = apps.get_model('contenttypes.contenttype')

    content_type = ContentType.objects.get_for_model(VirtualMachine)
    custom_statuses = Status.objects.filter(content_types=content_type)

    for virtualmachine in VirtualMachine.objects.all():
        virtualmachine.status_db = custom_statuses.get(name=virtualmachine.status)
        virtualmachine.save()


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('virtualization', '0022_vm_varchar_macaddress'),
    ]

    operations = [
        migrations.AddField(
            model_name='virtualmachine',
            name='status_db',
            field=extras.models.statuses.StatusField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='virtualmachines', to='extras.status'),
        ),
        migrations.RunPython(
            extras.management.populate_status_choices,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            populate_virtualmachine_status_db,
            migrations.RunPython.noop,
            hints={'model_name': 'virtualmachine'},
        ),
    ]
