import sys

from django.apps import apps as global_apps
from django.db import DEFAULT_DB_ALIAS, IntegrityError

from nautobot.utilities.choices import ColorChoices

# Map of css_class -> hex_color used when importing color choices in
# `export_statuses_from_choiceset()`. These hex_color values map to named color
# values defined in `utilities.choices.ColorChoices`.
COLOR_MAP = {
    "success": ColorChoices.COLOR_GREEN,  # active (green)
    "warning": ColorChoices.COLOR_AMBER,  # offline, decommissioning (amber)
    "info": ColorChoices.COLOR_CYAN,  # planned (cyan)
    "primary": ColorChoices.COLOR_BLUE,  # staged (blue)
    "danger": ColorChoices.COLOR_RED,  # failed (red)
    "default": ColorChoices.COLOR_GREY,  # inventory (grey)
}

# Map of slug -> description used when importing status choices in
# `export_statuses_from_choiceset()`.
DESCRIPTION_MAP = {
    "active": "Unit is active",
    "available": "Unit is available",
    "connected": "Cable is connected",
    "container": "Network contains children",
    "dhcp": "Dynamically assigned IPv4/IPv6 address",
    "decommissioned": "Circuit has been decommissioned",
    "decommissioning": "Unit is being decommissioned",
    "deprecated": "Unit has been deprecated",
    "deprovisioning": "Circuit is being deprovisioned",
    "failed": "Unit has failed",
    "inventory": "Device is in inventory",
    "offline": "Unit is offline",
    "planned": "Unit has been planned",
    "provisioning": "Circuit is being provisioned",
    "reserved": "Unit is reserved",
    "retired": "Site has been retired",
    "slaac": "Dynamically assigned IPv6 address",
    "staged": "Unit has been staged",
    "staging": "Site is in the process of being staged",
}


#
# Statuses
#


def populate_status_choices(apps, schema_editor, **kwargs):
    """
    Populate `Status` model choices.

    This will run the `create_custom_statuses` function during data migrations.

    When it is ran again post-migrate will be a noop.
    """

    app_config = apps.get_app_config("extras")
    create_custom_statuses(app_config, **kwargs)


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

    for slug, value in choiceset.CHOICES:
        css_class = choiceset.CSS_CLASSES[slug]

        choice_kwargs = dict(
            name=value,
            slug=slug,
            description=description_map[slug],
            color=color_map[css_class],
        )
        choices.append(choice_kwargs)

    return choices


def create_custom_statuses(
    app_config,
    verbosity=2,
    interactive=True,
    using=DEFAULT_DB_ALIAS,
    apps=global_apps,
    **kwargs,
):
    """
    Create database Status choices from choiceset enums.

    This is called during data migrations for importing `Status` objects from
    `ChoiceSet` enums in flat files.
    """
    if "test" in sys.argv:
        # Do not print output during unit testing migrations
        verbosity = 1

    if verbosity >= 0:
        print("\n", end="")

    # Prep the app and get the Status model dynamically
    try:
        Status = apps.get_model("extras.Status")
        ContentType = apps.get_model("contenttypes.ContentType")
    except LookupError:
        return

    # Import libs we need so we can map it for object creation.
    from nautobot.dcim import choices as dcim_choices
    from nautobot.circuits import choices as circuit_choices
    from nautobot.ipam import choices as ipam_choices
    from nautobot.virtualization import choices as vm_choices

    # List of 2-tuples of (model_path, choiceset)
    # Add new mappings here as other models are supported.
    CHOICESET_MAP = [
        ("dcim.Device", dcim_choices.DeviceStatusChoices),
        ("dcim.Site", dcim_choices.SiteStatusChoices),
        ("dcim.Rack", dcim_choices.RackStatusChoices),
        ("dcim.Cable", dcim_choices.CableStatusChoices),
        ("dcim.PowerFeed", dcim_choices.PowerFeedStatusChoices),
        ("circuits.Circuit", circuit_choices.CircuitStatusChoices),
        ("ipam.Prefix", ipam_choices.PrefixStatusChoices),
        ("ipam.IPAddress", ipam_choices.IPAddressStatusChoices),
        ("ipam.VLAN", ipam_choices.VLANStatusChoices),
        ("virtualization.VirtualMachine", vm_choices.VirtualMachineStatusChoices),
    ]

    added_total = 0
    linked_total = 0

    # Iterate choiceset kwargs to create status objects if they don't exist
    for model_path, choiceset in CHOICESET_MAP:
        content_type = ContentType.objects.get_for_model(apps.get_model(model_path))
        choices = export_statuses_from_choiceset(choiceset)

        if verbosity >= 2:
            print(f"    Model {model_path}", flush=True)

        for choice_kwargs in choices:
            # The value of `color` may differ between other enums. We'll need to
            # make sure they are normalized in `export_statuses_from_choiceset`
            # when we go to add `status` field for other object types.
            try:
                obj, created = Status.objects.get_or_create(**choice_kwargs)
            # This will likely be a duplicate key violation due to a Status
            # already existing (e.g. "active") albeit with a different `color`.
            # Pop the color and try again.
            except IntegrityError:
                choice_kwargs.pop("color")
                obj, created = Status.objects.get_or_create(**choice_kwargs)
            # If this subsequent .get_or_create fails, fail immediately.
            except Exception as err:
                raise SystemExit(
                    f"Unexpected error while running data migration to populate" f"status for {model_path}: {err}"
                )

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
