import json
import sys

from django.apps import apps as global_apps
from django.core.exceptions import FieldError
from django.core.management.base import CommandError
from django.db import DEFAULT_DB_ALIAS, IntegrityError
from django.utils import timezone
from django.utils.text import slugify

from nautobot.circuits import choices as circuit_choices
from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.choices import ColorChoices
from nautobot.dcim import choices as dcim_choices
from nautobot.extras import choices as extras_choices
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.jobs import get_job
from nautobot.extras.models import Job, JobLogEntry
from nautobot.ipam import choices as ipam_choices
from nautobot.virtualization import choices as vm_choices

# List of 2-tuples of (model_path, choiceset)
# Add new mappings here as other models are supported.
STATUS_CHOICESET_MAP = {
    "circuits.Circuit": circuit_choices.CircuitStatusChoices,
    "dcim.Cable": dcim_choices.CableStatusChoices,
    "dcim.Controller": dcim_choices.DeviceStatusChoices,
    "dcim.Device": dcim_choices.DeviceStatusChoices,
    "dcim.Interface": dcim_choices.InterfaceStatusChoices,
    "dcim.Location": dcim_choices.LocationStatusChoices,
    "dcim.Module": dcim_choices.ModuleStatusChoices,
    "dcim.PowerFeed": dcim_choices.PowerFeedStatusChoices,
    "dcim.Rack": dcim_choices.RackStatusChoices,
    "dcim.DeviceRedundancyGroup": dcim_choices.DeviceRedundancyGroupStatusChoices,
    "dcim.InterfaceRedundancyGroup": dcim_choices.InterfaceRedundancyGroupStatusChoices,
    "dcim.SoftwareImageFile": dcim_choices.SoftwareImageFileStatusChoices,
    "dcim.SoftwareVersion": dcim_choices.SoftwareVersionStatusChoices,
    "dcim.VirtualDeviceContext": dcim_choices.VirtualDeviceContextStatusChoices,
    "extras.ContactAssociation": extras_choices.ContactAssociationStatusChoices,
    "ipam.IPAddress": ipam_choices.IPAddressStatusChoices,
    "ipam.Prefix": ipam_choices.PrefixStatusChoices,
    "ipam.VLAN": ipam_choices.VLANStatusChoices,
    "ipam.VRF": ipam_choices.VRFStatusChoices,
    "virtualization.VirtualMachine": vm_choices.VirtualMachineStatusChoices,
    "virtualization.VMInterface": vm_choices.VMInterfaceStatusChoices,
}


# Map of status name -> default hex_color used when importing color choices in `export_statuses_from_choiceset()`.
# Only a small subset of colors are used by default as these originally were derived from Bootstrap CSS classes.
STATUS_COLOR_MAP = {
    "Active": ColorChoices.COLOR_GREEN,  # was COLOR_BLUE for Prefix/IPAddress/VLAN in NetBox
    "Available": ColorChoices.COLOR_GREEN,
    "Connected": ColorChoices.COLOR_GREEN,
    "DHCP": ColorChoices.COLOR_GREEN,
    "Decommissioned": ColorChoices.COLOR_GREY,
    "Decommissioning": ColorChoices.COLOR_AMBER,
    "Deprecated": ColorChoices.COLOR_RED,
    "Deprovisioning": ColorChoices.COLOR_AMBER,
    "Down": ColorChoices.COLOR_AMBER,
    "End-of-Life": ColorChoices.COLOR_RED,
    "Extended Support": ColorChoices.COLOR_CYAN,
    "Failed": ColorChoices.COLOR_RED,
    "Inventory": ColorChoices.COLOR_GREY,
    "Maintenance": ColorChoices.COLOR_GREY,
    "Offline": ColorChoices.COLOR_AMBER,
    "Planned": ColorChoices.COLOR_CYAN,
    "Primary": ColorChoices.COLOR_BLUE,
    "Provisioning": ColorChoices.COLOR_BLUE,
    "Reserved": ColorChoices.COLOR_CYAN,
    "Retired": ColorChoices.COLOR_RED,
    "Secondary": ColorChoices.COLOR_YELLOW,
    "SLAAC": ColorChoices.COLOR_GREEN,
    "Staged": ColorChoices.COLOR_BLUE,
    "Staging": ColorChoices.COLOR_BLUE,
}


# Map of status name -> description used when importing status choices in `export_statuses_from_choiceset()`.
STATUS_DESCRIPTION_MAP = {
    "Active": "Unit is active",
    "Available": "Unit is available",
    "Connected": "Cable is connected",
    "DHCP": "Dynamically assigned IPv4/IPv6 address",
    "Decommissioned": "Circuit has been decommissioned",
    "Decommissioning": "Unit is being decommissioned",
    "Deprecated": "Unit has been deprecated",
    "Deprovisioning": "Circuit is being deprovisioned",
    "Down": "VRF is down",
    "End-of-Life": "Unit has reached end-of-life",
    "Extended Support": "Software is in extended support",
    "Failed": "Unit has failed",
    "Inventory": "Device is in inventory",
    "Maintenance": "Unit is under maintenance",
    "Offline": "Unit is offline",
    "Planned": "Unit has been planned",
    "Primary": "Unit is primary",
    "Provisioning": "Circuit is being provisioned",
    "Reserved": "Unit is reserved",
    "Retired": "Location has been retired",
    "Secondary": "Unit is secondary",
    "SLAAC": "Dynamically assigned IPv6 address",
    "Staged": "Unit has been staged",
    "Staging": "Location is in the process of being staged",
}

# List of 2-tuples of (model_path, choiceset)
# Add new mappings here as other models are supported.
ROLE_CHOICESET_MAP = {
    "extras.ContactAssociation": extras_choices.ContactAssociationRoleChoices,
}

# Map of role name -> default hex_color used when importing color choices in `export_roles_from_choiceset()`.
# Only a small subset of colors are used by default as these originally were derived from Bootstrap CSS classes.
ROLE_COLOR_MAP = {
    "Administrative": ColorChoices.COLOR_BLUE,
    "Billing": ColorChoices.COLOR_GREEN,
    "Support": ColorChoices.COLOR_YELLOW,
    "On Site": ColorChoices.COLOR_BLACK,
}

# Map of role name -> description used when importing role choices in `export_roles_from_choiceset()`.
ROLE_DESCRIPTION_MAP = {
    "Administrative": "Unit plays an administrative role",
    "Billing": "Unit plays a billing role",
    "Support": "Unit plays a support role",
    "On Site": "Unit plays an on site role",
}


### Migration helper methods to populate/clear statuses and roles


def populate_status_choices(apps=global_apps, schema_editor=None, **kwargs):
    """
    Populate `Status` model choices.

    This will pass **kwargs to `_create_custom_role_or_status_instances` function and run it during data migrations.

    When it is ran again post-migrate will be a noop.
    """
    _create_custom_role_or_status_instances(apps=apps, metadatamodel="status", **kwargs)


def populate_role_choices(apps=global_apps, schema_editor=None, **kwargs):
    """
    Populate `Role` model choices.

     This will pass **kwargs to `_create_custom_role_or_status_instances` function and run it during data migrations.

    When it is ran again post-migrate will be a noop.
    """
    _create_custom_role_or_status_instances(apps=apps, metadatamodel="role", **kwargs)


def clear_status_choices(apps=global_apps, schema_editor=None, **kwargs):
    """
    Remove `Status` model choices.

    This will pass **kwargs to `_clear_custom_role_or_status_instances` function and run it during data migrations.

    When it is ran again post-migrate will be a noop.
    """
    _clear_custom_role_or_status_instances(apps=apps, metadatamodel="status", **kwargs)


def clear_role_choices(apps=global_apps, schema_editor=None, **kwargs):
    """
    Remove `Role` model choices.

    This will pass **kwargs to `_clear_custom_role_or_status_instances` function and run it during data migrations.

    When it is ran again post-migrate will be a noop.
    """
    _clear_custom_role_or_status_instances(apps=apps, metadatamodel="role", **kwargs)


def export_metadata_from_choiceset(choiceset, color_map=None, description_map=None, metadatamodel=None):
    """
    e.g. `export_metadata_from_choiceset(DeviceStatusChoices, content_type)`

    This is called by `extras.management._create_custom_role_or_status_instances` for use in
    performing data migrations to populate `Status` or `Role` objects.
    Args:
        choiceset (dict): A dictionary containing list of 2-tuples of (model_path, choiceset)
        color_map (dict): A dictionary of status/role name -> default hex_color
        description_map (dict): A dictionary of status/role name -> default description
        metadatamodel (str): "role" or "status"
    """
    if metadatamodel.lower() == "role":
        if color_map is None:
            color_map = ROLE_COLOR_MAP
        if description_map is None:
            description_map = ROLE_DESCRIPTION_MAP
    elif metadatamodel.lower() == "status":
        if color_map is None:
            color_map = STATUS_COLOR_MAP
        if description_map is None:
            description_map = STATUS_DESCRIPTION_MAP
    else:
        raise ValueError("only status and role are supported for export_metadata_from_choiceset")

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


def _create_custom_role_or_status_instances(
    app_config=None,  # unused
    verbosity=2,
    interactive=True,
    using=DEFAULT_DB_ALIAS,  # unused
    apps=global_apps,
    models=None,
    metadatamodel=None,
    **kwargs,
):
    """
    Create database Status choices from choiceset enums.

    This is called during data migrations for importing `Status` and `Role` objects from
    `ChoiceSet` enums in flat files.
    Args:
        models (dict): A list of model contenttype strings e.g. models=["circuits.Circuit", "dcim.Cable", "dcim.Device","dcim.PowerFeed"]
        metadatamodel (str): "role" or "status"
    """

    # Only print a newline if we have verbosity!
    if verbosity > 0:
        print("\n", end="")

    if "test" in sys.argv:
        # Do not print output during unit testing migrations
        verbosity = 1

    choiceset_map = {}
    if metadatamodel.lower() == "role":
        choiceset_map = ROLE_CHOICESET_MAP
        if not models:
            models = choiceset_map.keys()
    elif metadatamodel.lower() == "status":
        choiceset_map = STATUS_CHOICESET_MAP
        if not models:
            models = choiceset_map.keys()
    else:
        raise ValueError("only status and role are supported for _create_custom_role_or_status_instances")

    # Prep the app and get the model dynamically
    try:
        MetadataModel = apps.get_model(f"extras.{metadatamodel}")
        ContentType = apps.get_model("contenttypes.ContentType")
    except LookupError:
        raise LookupError(
            f"Could not find extras.{metadatamodel} and/or contenttypes.ContentType. Please make sure the correct migration dependencies are set before using this method"
        )

    added_total = 0
    linked_total = 0

    # Iterate choiceset kwargs to create status objects if they don't exist
    for model_path in models:
        choiceset = choiceset_map[model_path]
        content_type = ContentType.objects.get_for_model(apps.get_model(model_path))
        choices = export_metadata_from_choiceset(choiceset, metadatamodel=metadatamodel)

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
                obj, created = MetadataModel.objects.get_or_create(slug=slug, defaults=defaults)
            except (IntegrityError, FieldError) as error:
                # OK, what if we look up by name instead?
                defaults = choice_kwargs.copy()
                name = defaults.pop("name")
                # FieldError would occur when calling create_custom_statuses after status slug removal
                # migration has been migrated
                # e.g nautobot.extras.tests.test_management.MetadataManagementTestCase.test_populate_status_choices_idempotent
                if isinstance(error, FieldError):
                    defaults.pop("slug")
                try:
                    obj, created = MetadataModel.objects.get_or_create(name=name, defaults=defaults)
                except IntegrityError as err:
                    raise SystemExit(
                        f"Unexpected error while running data migration to populate {metadatamodel} for {model_path}: {err}"
                    ) from err

            # Make sure the content-type is associated.
            if content_type not in obj.content_types.all():
                obj.content_types.add(content_type)

            if created and verbosity >= 2:
                print(f"      Adding and linking {metadatamodel} {obj.name}", flush=True)
                added_total += 1
            elif not created and verbosity >= 2:
                print(f"      Linking to existing {metadatamodel} {obj.name}", flush=True)
                linked_total += 1

    if verbosity >= 2:
        print(f"    Added {added_total}, linked {linked_total} {metadatamodel} records")


def _clear_custom_role_or_status_instances(
    apps=global_apps,
    schema_editor=None,
    verbosity=2,
    models=None,
    metadatamodel=None,
    clear_all_model_statuses=True,
    **kwargs,
):
    """
    Remove content types from statuses/roles, and if no content types remain, delete the status/role instance as well.
    Args:
        models (dict): A list of model contenttype strings e.g. models=["circuits.Circuit", "dcim.Cable", "dcim.Device","dcim.PowerFeed"]
        metadatamodel (str): "role" or "status"
        clear_all_model_statuses (bool): Set it to True will clear all statuses for this model. Set it to False will only clear default statuses for this model.
    """
    if "test" in sys.argv:
        # Do not print output during unit testing migrations
        verbosity = 1

    choiceset_map = {}
    if metadatamodel.lower() == "role":
        choiceset_map = ROLE_CHOICESET_MAP
        if not models:
            models = choiceset_map.keys()
    elif metadatamodel.lower() == "status":
        choiceset_map = STATUS_CHOICESET_MAP
        if not models:
            models = choiceset_map.keys()
    else:
        raise ValueError("only status and role are supported for _clear_custom_role_or_status_instances")

    # Prep the app and get the model dynamically
    try:
        MetadataModel = apps.get_model(f"extras.{metadatamodel}")
        ContentType = apps.get_model("contenttypes.ContentType")
    except LookupError:
        raise LookupError(
            f"Could not find extras.{metadatamodel} and/or contenttypes.ContentType. Please make sure the correct migration dependencies are set before using this method"
        )

    deleted_total = 0
    unlinked_total = 0

    for model_path in models:
        choiceset = choiceset_map[model_path]
        model = apps.get_model(model_path)
        content_type = ContentType.objects.get_for_model(model)
        choices = export_metadata_from_choiceset(choiceset, metadatamodel=metadatamodel)

        if verbosity >= 2:
            print(f"    Model {model_path}", flush=True)

        if not clear_all_model_statuses:
            # Only clear default statuses/roles for this model
            names = [choice_kwargs["name"] for choice_kwargs in choices]
        else:
            # Clear all statuses/roles for this model
            names = MetadataModel.objects.filter(content_types=content_type).values_list("name", flat=True)

        for name in names:
            try:
                obj = MetadataModel.objects.get(name=name)
                obj.content_types.remove(content_type)
                if not obj.content_types.all().exists():
                    obj.delete()
                    if verbosity >= 2:
                        print(f"      Deleting {metadatamodel} {obj.name}", flush=True)
                    deleted_total += 1
                else:
                    if verbosity >= 2:
                        print(f"      Unlinking {metadatamodel} {obj.name}", flush=True)
                    unlinked_total += 1
            except Exception as err:
                raise SystemExit(
                    f"Unexpected error while running data migration to remove {metadatamodel} {name} for {model_path}: {err}"
                )

    if verbosity >= 2:
        print(f"    Deleted {deleted_total}, unlinked {unlinked_total} {metadatamodel} records")


def validate_job_and_job_data(command, user, job_class_path, data=None):
    job_data = {}
    try:
        if data:
            job_data = json.loads(data, cls=NautobotKombuJSONEncoder)
    except json.decoder.JSONDecodeError as error:
        raise CommandError(f"Invalid JSON data:\n{error!s}") from error

    if not get_job(job_class_path, reload=True):
        raise CommandError(f'Job "{job_class_path}" not found')

    try:
        job_model = Job.objects.get_for_class_path(job_class_path)
    except Job.DoesNotExist as error:
        raise CommandError(f"Job {job_class_path} does not exist.") from error

    try:
        job_model = Job.objects.restrict(user, "run").get_for_class_path(job_class_path)
    except Job.DoesNotExist:
        raise CommandError(f"User {user.username} does not have permission to run this Job") from None

    if not job_model.installed or job_model.job_class is None:
        raise CommandError("Job is not presently installed")
    if not job_model.enabled:
        raise CommandError("Job is not presently enabled to be run")

    # Run the job and create a new JobResult
    command.stdout.write(f"[{timezone.now():%H:%M:%S}] Running {job_class_path}...")
    return job_data


def report_job_status(command, job_result):
    # Report on success/failure
    job_class_path = job_result.job_model.class_path
    groups = set(JobLogEntry.objects.filter(job_result=job_result).values_list("grouping", flat=True))
    for group in sorted(groups):
        logs = JobLogEntry.objects.filter(job_result__pk=job_result.pk, grouping=group)
        debug_count = logs.filter(log_level=LogLevelChoices.LOG_DEBUG).count()
        info_count = logs.filter(log_level=LogLevelChoices.LOG_INFO).count()
        warning_count = logs.filter(log_level=LogLevelChoices.LOG_WARNING).count()
        error_count = logs.filter(log_level=LogLevelChoices.LOG_ERROR).count()
        critical_count = logs.filter(log_level=LogLevelChoices.LOG_CRITICAL).count()

        command.stdout.write(
            f"\t{group}: {debug_count} debug, {info_count} info, {warning_count} warning, {error_count} error, {critical_count} critical"
        )

        for log_entry in logs:
            status = log_entry.log_level
            if status == "success":
                status = command.style.SUCCESS(status)
            elif status == "info":
                status = status
            elif status == "warning":
                status = command.style.WARNING(status)
            elif status == "failure":
                status = command.style.NOTICE(status)

            if log_entry.log_object:
                command.stdout.write(f"\t\t{status}: {log_entry.log_object}: {log_entry.message}")
            else:
                command.stdout.write(f"\t\t{status}: {log_entry.message}")

    if job_result.result:
        command.stdout.write(str(job_result.result))

    if job_result.status == JobResultStatusChoices.STATUS_FAILURE:
        status = command.style.ERROR("FAILURE")
    elif job_result.status == JobResultStatusChoices.STATUS_SUCCESS:
        status = command.style.SUCCESS("SUCCESS")
    else:
        status = command.style.WARNING(job_result.status)
    command.stdout.write(f"[{timezone.now():%H:%M:%S}] {job_class_path}: {status}")

    # Wrap things up
    command.stdout.write(f"[{timezone.now():%H:%M:%S}] {job_class_path}: Duration {job_result.duration}")
    command.stdout.write(f"[{timezone.now():%H:%M:%S}] Finished")
