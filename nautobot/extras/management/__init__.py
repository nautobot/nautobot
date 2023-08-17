import sys

from django.apps import apps as global_apps
from django.core.exceptions import FieldError
from django.db import DEFAULT_DB_ALIAS, IntegrityError
from django.utils.text import slugify

from nautobot.circuits import choices as circuit_choices
from nautobot.core.choices import ColorChoices
from nautobot.dcim import choices as dcim_choices
from nautobot.ipam import choices as ipam_choices
from nautobot.virtualization import choices as vm_choices


# List of 2-tuples of (model_path, choiceset)
# Add new mappings here as other models are supported.
CHOICESET_MAP = {
    "circuits.Circuit": circuit_choices.CircuitStatusChoices,
    "dcim.Cable": dcim_choices.CableStatusChoices,
    "dcim.Device": dcim_choices.DeviceStatusChoices,
    "dcim.Interface": dcim_choices.InterfaceStatusChoices,
    "dcim.Location": dcim_choices.LocationStatusChoices,
    "dcim.PowerFeed": dcim_choices.PowerFeedStatusChoices,
    "dcim.Rack": dcim_choices.RackStatusChoices,
    "dcim.DeviceRedundancyGroup": dcim_choices.DeviceRedundancyGroupStatusChoices,
    "dcim.InterfaceRedundancyGroup": dcim_choices.InterfaceRedundancyGroupStatusChoices,
    "ipam.IPAddress": ipam_choices.IPAddressStatusChoices,
    "ipam.Prefix": ipam_choices.PrefixStatusChoices,
    "ipam.VLAN": ipam_choices.VLANStatusChoices,
    "virtualization.VirtualMachine": vm_choices.VirtualMachineStatusChoices,
    "virtualization.VMInterface": vm_choices.VMInterfaceStatusChoices,
}


# Map of status name -> default hex_color used when importing color choices in `export_statuses_from_choiceset()`.
# Only a small subset of colors are used by default as these originally were derived from Bootstrap CSS classes.
COLOR_MAP = {
    "Active": ColorChoices.COLOR_GREEN,  # was COLOR_BLUE for Prefix/IPAddress/VLAN in NetBox
    "Available": ColorChoices.COLOR_GREEN,
    "Connected": ColorChoices.COLOR_GREEN,
    "DHCP": ColorChoices.COLOR_GREEN,
    "Decommissioned": ColorChoices.COLOR_GREY,
    "Decommissioning": ColorChoices.COLOR_AMBER,
    "Deprecated": ColorChoices.COLOR_RED,
    "Deprovisioning": ColorChoices.COLOR_AMBER,
    "Failed": ColorChoices.COLOR_RED,
    "Inventory": ColorChoices.COLOR_GREY,
    "Maintenance": ColorChoices.COLOR_GREY,
    "Offline": ColorChoices.COLOR_AMBER,
    "Planned": ColorChoices.COLOR_CYAN,
    "Provisioning": ColorChoices.COLOR_BLUE,
    "Reserved": ColorChoices.COLOR_CYAN,
    "Retired": ColorChoices.COLOR_RED,
    "SLAAC": ColorChoices.COLOR_GREEN,
    "Staged": ColorChoices.COLOR_BLUE,
    "Staging": ColorChoices.COLOR_BLUE,
}


# Map of status name -> description used when importing status choices in `export_statuses_from_choiceset()`.
DESCRIPTION_MAP = {
    "Active": "Unit is active",
    "Available": "Unit is available",
    "Connected": "Cable is connected",
    "DHCP": "Dynamically assigned IPv4/IPv6 address",
    "Decommissioned": "Circuit has been decommissioned",
    "Decommissioning": "Unit is being decommissioned",
    "Deprecated": "Unit has been deprecated",
    "Deprovisioning": "Circuit is being deprovisioned",
    "Failed": "Unit has failed",
    "Inventory": "Device is in inventory",
    "Maintenance": "Unit is under maintenance",
    "Offline": "Unit is offline",
    "Planned": "Unit has been planned",
    "Provisioning": "Circuit is being provisioned",
    "Reserved": "Unit is reserved",
    "Retired": "Location has been retired",
    "SLAAC": "Dynamically assigned IPv6 address",
    "Staged": "Unit has been staged",
    "Staging": "Location is in the process of being staged",
}


#
# Statuses
#


def populate_status_choices(apps=global_apps, schema_editor=None, **kwargs):
    """
    Populate `Status` model choices.

    This will run the `create_custom_statuses` function during data migrations.

    When it is ran again post-migrate will be a noop.
    """
    create_custom_statuses(apps=apps, **kwargs)


def export_statuses_from_choiceset(choiceset, color_map=None, description_map=None):
    """
    e.g. `export_choices_from_choiceset(DeviceStatusChoices, content_type)`

    This is called by `extras.management.create_custom_statuses` for use in
    performing data migrations to populate `Status` objects.
    """

    if color_map is None:
        color_map = COLOR_MAP
    if description_map is None:
        description_map = DESCRIPTION_MAP

    choices = []

    for _, value in choiceset.CHOICES:
        choice_kwargs = {
            "name": value,
            "description": description_map[value],
            "slug": slugify(value),
            "color": color_map[value],
        }
        choices.append(choice_kwargs)

    return choices


def create_custom_statuses(
    app_config=None,  # unused
    verbosity=2,
    interactive=True,
    using=DEFAULT_DB_ALIAS,  # unused
    apps=global_apps,
    models=None,
    **kwargs,
):
    """
    Create database Status choices from choiceset enums.

    This is called during data migrations for importing `Status` objects from
    `ChoiceSet` enums in flat files.
    """

    # Only print a newline if we have verbosity!
    if verbosity > 0:
        print("\n", end="")

    if "test" in sys.argv:
        # Do not print output during unit testing migrations
        verbosity = 1

    if not models:
        models = CHOICESET_MAP.keys()

    # Prep the app and get the Status model dynamically
    try:
        Status = apps.get_model("extras.Status")
        ContentType = apps.get_model("contenttypes.ContentType")
    except LookupError:
        return

    added_total = 0
    linked_total = 0

    # Iterate choiceset kwargs to create status objects if they don't exist
    for model_path in models:
        choiceset = CHOICESET_MAP[model_path]
        content_type = ContentType.objects.get_for_model(apps.get_model(model_path))
        choices = export_statuses_from_choiceset(choiceset)

        if verbosity >= 2:
            print(f"    Model {model_path}", flush=True)

        for choice_kwargs in choices:
            # Since statuses are customizable now, we need to gracefully handle the case where a status
            # has had its name, slug, color and/or description changed from the defaults.
            # First, try to find by slug if applicable
            defaults = choice_kwargs.copy()
            slug = defaults.pop("slug")
            try:
                # May fail with an IntegrityError if a status with a different slug has a name matching this one
                # May fail with a FieldError if the Status model no longer has a slug field
                obj, created = Status.objects.get_or_create(slug=slug, defaults=defaults)
            except (IntegrityError, FieldError) as error:
                # OK, what if we look up by name instead?
                defaults = choice_kwargs.copy()
                name = defaults.pop("name")
                # FieldError would occur when calling create_custom_statuses after status slug removal
                # migration has been migrated
                # e.g nautobot.extras.tests.test_management.StatusManagementTestCase.test_populate_status_choices_idempotent
                if isinstance(error, FieldError):
                    defaults.pop("slug")
                try:
                    obj, created = Status.objects.get_or_create(name=name, defaults=defaults)
                except IntegrityError as err:
                    raise SystemExit(
                        f"Unexpected error while running data migration to populate status for {model_path}: {err}"
                    ) from err

            # Make sure the content-type is associated.
            if content_type not in obj.content_types.all():
                obj.content_types.add(content_type)

            if created and verbosity >= 2:
                print(f"      Adding and linking status {obj.name}", flush=True)
                added_total += 1
            elif not created and verbosity >= 2:
                print(f"      Linking to existing status {obj.name}", flush=True)
                linked_total += 1

    if verbosity >= 2:
        print(f"    Added {added_total}, linked {linked_total} status records")


def clear_status_choices(
    apps=global_apps,
    schema_editor=None,
    verbosity=2,
    models=None,
    clear_all_model_statuses=True,
    **kwargs,
):
    """
    Remove content types from statuses, and if no content types remain, delete the statuses as well.
    """
    if "test" in sys.argv:
        # Do not print output during unit testing migrations
        verbosity = 1

    if verbosity >= 0:
        print("\n", end="")

    if not models:
        models = CHOICESET_MAP.keys()

    Status = apps.get_model("extras.Status")
    ContentType = apps.get_model("contenttypes.ContentType")

    deleted_total = 0
    unlinked_total = 0

    for model_path in models:
        choiceset = CHOICESET_MAP[model_path]
        model = apps.get_model(model_path)
        content_type = ContentType.objects.get_for_model(model)
        choices = export_statuses_from_choiceset(choiceset)

        if verbosity >= 2:
            print(f"    Model {model_path}", flush=True)

        if not clear_all_model_statuses:
            # Only clear default statuses for this model
            names = [choice_kwargs["name"] for choice_kwargs in choices]
        else:
            # Clear all statuses for this model
            names = Status.objects.filter(content_types=content_type).values_list("name", flat=True)

        for name in names:
            try:
                obj = Status.objects.get(name=name)
                obj.content_types.remove(content_type)
                if not obj.content_types.all().exists():
                    obj.delete()
                    if verbosity >= 2:
                        print(f"      Deleting status {obj.name}", flush=True)
                    deleted_total += 1
                else:
                    if verbosity >= 2:
                        print(f"      Unlinking status {obj.name}", flush=True)
                    unlinked_total += 1
            except Exception as err:
                raise SystemExit(
                    f"Unexpected error while running data migration to remove status for {model_path}: {err}"
                )

    if verbosity >= 2:
        print(f"    Deleted {deleted_total}, unlinked {unlinked_total} status records")
