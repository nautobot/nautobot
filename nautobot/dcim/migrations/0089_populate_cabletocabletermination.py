"""Data migration: populate CableToCableTermination rows from the legacy Cable GFK fields.

Each CableToCableTermination row is keyed by exactly one of nine type-specific FK fields. This
migration translates the legacy `Cable.termination_a_type` / `Cable.termination_a_id` GFK pair (and
B-side) into a write to the appropriate FK column on the join model.
"""

from django.db import migrations

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

    # Cache content types so we don't requery per-row.
    ct_cache = {}

    def _fk_field_for(ct_id):
        if ct_id not in ct_cache:
            ct = ContentType.objects.get(pk=ct_id)
            ct_cache[ct_id] = _FK_FIELD_BY_NATURAL_KEY.get((ct.app_label, ct.model))
        return ct_cache[ct_id]

    for cable in Cable.objects.all().iterator():
        for cable_end, type_id, term_id, device_id in (
            (
                "A",
                cable.termination_a_type_id,
                cable.termination_a_id,
                getattr(cable, "_termination_a_device_id", None),
            ),
            (
                "B",
                cable.termination_b_type_id,
                cable.termination_b_id,
                getattr(cable, "_termination_b_device_id", None),
            ),
        ):
            if not (type_id and term_id):
                continue
            fk_field = _fk_field_for(type_id)
            if fk_field is None:
                continue
            CableToCableTermination.objects.get_or_create(
                cable=cable,
                cable_end=cable_end,
                **{fk_field: term_id},
                defaults={"_termination_device_id": device_id},
            )


class Migration(migrations.Migration):
    dependencies = [("dcim", "0088_cabletocabletermination")]
    operations = [migrations.RunPython(populate_cable_to_cable_terminations, migrations.RunPython.noop)]
