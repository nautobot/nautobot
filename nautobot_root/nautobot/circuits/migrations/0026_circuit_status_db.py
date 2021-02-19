from django.db import migrations
import django.db.models.deletion
import nautobot.extras.models.statuses


def populate_circuit_status_db(apps, schema_editor):
    """
    Iterate existing Circuits and populate `status_db` from `status` field.
    """
    Status = apps.get_model('extras.status')
    Circuit = apps.get_model('circuits.Circuit')
    ContentType = apps.get_model('contenttypes.contenttype')

    content_type = ContentType.objects.get_for_model(Circuit)
    custom_statuses = Status.objects.filter(content_types=content_type)

    for circuit in Circuit.objects.all():
        circuit.status_db = custom_statuses.get(slug=circuit.status)
        circuit.save()


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0061_status_custom_field_data'),
        ('circuits', '0025_add_custom_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='circuit',
            name='status_db',
            field=nautobot.extras.models.statuses.StatusField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='circuits_circuit_related', to='extras.status'),
        ),
        migrations.RunPython(
            populate_circuit_status_db,
            migrations.RunPython.noop,
            hints={'model_name': 'circuit'},
        ),
    ]
