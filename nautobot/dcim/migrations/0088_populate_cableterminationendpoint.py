"""Data migration: populate CableTerminationEndpoint from Cable GFK fields."""

from django.db import migrations


def populate_cable_termination_endpoints(apps, schema_editor):
    Cable = apps.get_model("dcim", "Cable")
    CableTerminationEndpoint = apps.get_model("dcim", "CableTerminationEndpoint")
    for cable in Cable.objects.all().iterator():
        if cable.termination_a_type_id and cable.termination_a_id:
            CableTerminationEndpoint.objects.get_or_create(
                termination_type_id=cable.termination_a_type_id,
                termination_id=cable.termination_a_id,
                defaults={
                    "cable": cable,
                    "cable_end": "A",
                    "_termination_device_id": getattr(cable, "_termination_a_device_id", None),
                },
            )
        if cable.termination_b_type_id and cable.termination_b_id:
            CableTerminationEndpoint.objects.get_or_create(
                termination_type_id=cable.termination_b_type_id,
                termination_id=cable.termination_b_id,
                defaults={
                    "cable": cable,
                    "cable_end": "B",
                    "_termination_device_id": getattr(cable, "_termination_b_device_id", None),
                },
            )


class Migration(migrations.Migration):
    dependencies = [("dcim", "0087_cable_termination_endpoint")]
    operations = [migrations.RunPython(populate_cable_termination_endpoints, migrations.RunPython.noop)]
