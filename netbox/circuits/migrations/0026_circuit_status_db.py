from django.db import migrations
import django.db.models.deletion
import extras.models.statuses
import extras.management


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
        circuit.status_db = custom_statuses.get(name=circuit.status)
        circuit.save()


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0057_status_field'),
        ('circuits', '0025_add_custom_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='circuit',
            name='status_db',
            field=extras.models.statuses.StatusField(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='circuits', to='extras.status'),
        ),
        migrations.RunPython(
            extras.management.populate_status_choices,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            populate_circuit_status_db,
            migrations.RunPython.noop,
            hints={'model_name': 'circuit'},
        ),
    ]
