"""Data migration: populate CableToCableTermination rows from the legacy Cable GFK fields.

Each CableToCableTermination row is keyed by exactly one of nine type-specific FK fields. This
migration translates the legacy `Cable.termination_a_type` / `Cable.termination_a_id` GFK pair (and
B-side) into a write to the appropriate FK column on the join model.
"""

from functools import reduce
import operator

from django.db import migrations, models

# Map (app_label, model_name) of a legacy GFK target → the corresponding FK field name on
# CableToCableTermination.
_FK_FIELD_BY_NATURAL_KEY = {
    ("circuits", "circuittermination"): "circuit_termination_id",
    ("dcim", "consoleport"): "console_port_id",
    ("dcim", "consoleserverport"): "console_server_port_id",
    ("dcim", "frontport"): "front_port_id",
    ("dcim", "interface"): "interface_id",
    ("dcim", "powerfeed"): "power_feed_id",
    ("dcim", "poweroutlet"): "power_outlet_id",
    ("dcim", "powerport"): "power_port_id",
    ("dcim", "rearport"): "rear_port_id",
}


def populate_cable_to_cable_terminations(apps, schema_editor):
    Cable = apps.get_model("dcim", "Cable")
    CableToCableTermination = apps.get_model("dcim", "CableToCableTermination")
    ContentType = apps.get_model("contenttypes", "ContentType")

    ct_filter = reduce(
        operator.or_,
        (models.Q(app_label=app_label, model=model) for app_label, model in _FK_FIELD_BY_NATURAL_KEY),
    )
    fk_field_by_ct_id = {
        ct.pk: _FK_FIELD_BY_NATURAL_KEY[(ct.app_label, ct.model)] for ct in ContentType.objects.filter(ct_filter)
    }

    def _new_termination(cable_id, cable_end, type_id, term_id):
        if not (type_id and term_id):
            return None
        fk_field = fk_field_by_ct_id.get(type_id)
        if fk_field is None:
            return None
        return CableToCableTermination(cable_id=cable_id, cable_end=cable_end, **{fk_field: term_id})

    batch = []
    batch_size = 2000
    cable_fields = ("pk", "termination_a_type_id", "termination_a_id", "termination_b_type_id", "termination_b_id")
    for pk, a_type, a_id, b_type, b_id in Cable.objects.values_list(*cable_fields).iterator(chunk_size=batch_size):
        for cable_end, type_id, term_id in (("A", a_type, a_id), ("B", b_type, b_id)):
            obj = _new_termination(pk, cable_end, type_id, term_id)
            if obj is not None:
                batch.append(obj)
        if len(batch) >= batch_size:
            CableToCableTermination.objects.bulk_create(batch, ignore_conflicts=True)
            batch = []

    if batch:
        CableToCableTermination.objects.bulk_create(batch, ignore_conflicts=True)


def clear_cable_to_cable_terminations(apps, schema_editor):
    CableToCableTermination = apps.get_model("dcim", "CableToCableTermination")
    CableToCableTermination.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("dcim", "0088_cabletocabletermination")]
    operations = [migrations.RunPython(populate_cable_to_cable_terminations, clear_cable_to_cable_terminations)]
