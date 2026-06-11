# Generated migration: back-populate the root device FK on all modular component rows
# that are currently attached via a module only.
#
# Data model
# ----------
# dcim_modulebay:
#   parent_device  – set when the bay belongs directly to a device (top-level bay)
#   parent_module  – set when the bay belongs to a nested module
#
# dcim_module:
#   parent_module_bay – the bay this module is installed in (OneToOneField)
#
# ModularComponentModel subclasses (Interface, ConsolePort, ConsoleServerPort,
#   PowerPort, PowerOutlet, FrontPort, RearPort):
#   device  – root device shortcut (what we are filling)
#   module  – immediate parent module
#
# Strategy
# --------
# Phase 1 - ModuleBay backfill (level by level):
#   Iterate until all ModuleBay rows with parent_module set have parent_device
#   populated. Each pass resolves one more level of nesting by looking up
#   parent_module.parent_module_bay.parent_device, which is valid for bays whose
#   immediate parent bay was resolved in the previous pass.
#
# Phase 2 - ModularComponentModel backfill:
#   By this point all ModuleBay rows have parent_device populated, so each
#   component can resolve its root device in a single lookup via
#   module.parent_module_bay.parent_device.

from django.db import migrations

CHUNK_SIZE = 2000


def backpopulate_device(apps, schema_editor):
    db = schema_editor.connection.alias

    ModuleBay = apps.get_model("dcim", "ModuleBay")

    while True:
        unresolved_bays = (
            ModuleBay.objects.using(db)
            .filter(
                parent_device__isnull=True,
                parent_module__isnull=False,
                parent_module__parent_module_bay__parent_device__isnull=False,
            )
            .select_related("parent_module__parent_module_bay__parent_device")
        )

        updates = []
        for bay in unresolved_bays.iterator(chunk_size=CHUNK_SIZE):
            bay.parent_device = bay.parent_module.parent_module_bay.parent_device
            updates.append(bay)

            if len(updates) >= CHUNK_SIZE:
                ModuleBay.objects.using(db).bulk_update(updates, ["parent_device"])
                updates.clear()

        if updates:
            ModuleBay.objects.using(db).bulk_update(updates, ["parent_device"])

        # If nothing was resolved in this pass, all remaining unresolved bays
        # are spares (no device reachable) — stop iterating.
        if not updates and not unresolved_bays.exists():
            break

    component_models = [
        apps.get_model("dcim", "ConsolePort"),
        apps.get_model("dcim", "ConsoleServerPort"),
        apps.get_model("dcim", "PowerPort"),
        apps.get_model("dcim", "PowerOutlet"),
        apps.get_model("dcim", "FrontPort"),
        apps.get_model("dcim", "RearPort"),
        apps.get_model("dcim", "Interface"),
    ]

    for model in component_models:
        unresolved = (
            model.objects.using(db)
            .filter(
                device__isnull=True,
                module__isnull=False,
                module__parent_module_bay__parent_device__isnull=False,
            )
            .select_related("module__parent_module_bay__parent_device")
        )

        updates = []
        for component in unresolved.iterator(chunk_size=CHUNK_SIZE):
            component.device = component.module.parent_module_bay.parent_device
            updates.append(component)

            if len(updates) >= CHUNK_SIZE:
                model.objects.using(db).bulk_update(updates, ["device"])
                updates.clear()

        if updates:
            model.objects.using(db).bulk_update(updates, ["device"])


def clear_backpopulated_device(apps, schema_editor):
    db = schema_editor.connection.alias

    ModuleBay = apps.get_model("dcim", "ModuleBay")
    component_models = [
        apps.get_model("dcim", "ConsolePort"),
        apps.get_model("dcim", "ConsoleServerPort"),
        apps.get_model("dcim", "PowerPort"),
        apps.get_model("dcim", "PowerOutlet"),
        apps.get_model("dcim", "FrontPort"),
        apps.get_model("dcim", "RearPort"),
        apps.get_model("dcim", "Interface"),
    ]

    for model in component_models:
        model.objects.using(db).filter(module__isnull=False).update(device=None)

    ModuleBay.objects.using(db).filter(parent_module__isnull=False).update(parent_device=None)


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0091_remove_consoleport_dcim_consoleport_device_name_unique_and_more"),
    ]

    operations = [
        migrations.RunPython(
            code=backpopulate_device,
            reverse_code=clear_backpopulated_device,
            hints={"target_db": "default"},
        ),
    ]
