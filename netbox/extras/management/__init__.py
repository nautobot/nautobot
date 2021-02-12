from django.apps import apps as global_apps
from django.db import DEFAULT_DB_ALIAS, IntegrityError


#
# Statuses
#

def populate_status_choices(apps, schema_editor, **kwargs):
    """
    Explicitly run the `create_custom_statuses` signal since it is only ran at
    post-migrate.

    When it is ran again post-migrate will be a noop.
    """
    app_config = apps.get_app_config('extras')
    create_custom_statuses(app_config, **kwargs)


def export_statuses_from_choiceset(choiceset):
    """
    e.g. `export_choices_from_choiceset(DeviceStatusChoices, content_type)`

    This is called by `extras.management.create_custom_statuses` for use in
    performing data migrations to populate `Status` objects.
    """
    choices = []

    # Map of css_class -> hex_color
    COLOR_MAP = {
        "success": "5cb85c",  # active
        "warning": "f0ad4e",  # offline, decommissioning
        "info": "5bc0de",  # planned
        "primary": "337ab7",  # staged
        "danger": "d9534f",  # failed
        "default": "777777",  # inventory
    }

    for value_lower, value in choiceset.CHOICES:
        css_class = choiceset.CSS_CLASSES[value_lower]

        choice_kwargs = dict(
            name=value_lower,
            color=COLOR_MAP[css_class],
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

    # Prep the app and get the Status model dynamically
    try:
        Status = apps.get_model("extras.Status")
        ContentType = apps.get_model("contenttypes.ContentType")
    except LookupError:
        return

    # Import libs we need so we can map it for object creation.
    from dcim import choices as dcim_choices

    # List of 2-tuples of (model_path, choiceset)
    # Add new mappings here as other models are supported.
    CHOICESET_MAP = [
        ("dcim.Device", dcim_choices.DeviceStatusChoices),
        ("dcim.Site", dcim_choices.SiteStatusChoices),
        ("dcim.Rack", dcim_choices.RackStatusChoices),
        ("dcim.Cable", dcim_choices.CableStatusChoices),
    ]

    # Iterate choiceset kwargs to create status objects if they don't exist
    for model_path, choiceset in CHOICESET_MAP:
        content_type = ContentType.objects.get_for_model(apps.get_model(model_path))
        choices = export_statuses_from_choiceset(choiceset)

        for choice_kwargs in choices:
            # TODO(jathan): I'm concerned that `color` value may differ between
            # other enums. We'll need to make sure they are normalized in
            # `export_statuses_from_choiceset` when we go to add `status` field
            # for other object types.
            try:
                obj, created = Status.objects.get_or_create(**choice_kwargs)
            # This will likely be a duplicate key violation due to a Status
            # already existing (e.g. "active") albeit with a different `color`.
            # Pop the color and try again.
            except IntegrityError as err:
                choice_kwargs.pop('color')
                obj, created = Status.objects.get_or_create(**choice_kwargs)
            # If this subsequent .get_or_create fails, fail immediately.
            except Exception as err:
                raise SystemExit(
                    f'Unexpected error while running data migration to populate'
                    f'status for {model_path}: {err}'
                )

            # Make sure the content-type is associated.
            obj.content_types.add(content_type)

            if created and verbosity >= 2:
                print(f"Adding status {model_path} | {obj.name}")
