import functools
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.dispatch import receiver

from nautobot.core.signals import disable_for_loaddata

from .models import (
    Cable,
    CablePath,
    CableToCableTermination,
    ConsolePort,
    ConsoleServerPort,
    ControllerManagedDeviceGroup,
    Device,
    DeviceRedundancyGroup,
    FrontPort,
    Interface,
    InterfaceVDCAssignment,
    LocationType,
    PathEndpoint,
    PowerFeed,
    PowerOutlet,
    PowerPanel,
    PowerPort,
    Rack,
    RackGroup,
    RearPort,
    VirtualChassis,
)
from .utils import validate_interface_tagged_vlans


def create_cablepath(node, rebuild=True):
    """
    Create CablePaths for all paths originating from the specified node.

    For breakout cables, creates one CablePath per fan-out lane mapped to this
    node's connector via the template.

    rebuild (bool) - Used to refresh paths where this node is not an endpoint.
    """
    from nautobot.dcim.models import CableToCableTermination

    if not node.cable_id:
        if rebuild:
            rebuild_paths(node)
        return

    cable = node.cable

    # Check if this is a breakout cable with multiple far-side lanes
    if cable.cable_type_id:
        my_endpoint = CableToCableTermination.objects.filter(cable=cable, termination_id=node.pk).first()

        if my_endpoint and my_endpoint.connector is not None:
            opposite_side = "B" if my_endpoint.cable_end == "A" else "A"
            origin_side_key = "a_connector" if my_endpoint.cable_end == "A" else "b_connector"
            far_side_key = "b_connector" if my_endpoint.cable_end == "A" else "a_connector"

            # Find all far-side endpoints mapped to this origin's connector
            far_position_key = "b_position" if my_endpoint.cable_end == "A" else "a_position"
            for mapping_entry in cable.cable_type.mapping:
                if mapping_entry[origin_side_key] == my_endpoint.connector:
                    far_connector = mapping_entry[far_side_key]
                    far_position = mapping_entry.get(far_position_key, 1)

                    # Find the actual far-end termination for this lane
                    far_ep = CableToCableTermination.objects.filter(
                        cable=cable,
                        cable_end=opposite_side,
                        connector=far_connector,
                    ).first()
                    far_term = far_ep.termination if far_ep else None

                    # Trace the path for this specific lane, overriding the first hop's peer
                    cable_path = CablePath.from_origin(node, far_end_override=far_term)
                    if cable_path:
                        cable_path.connector = far_connector
                        cable_path.position = far_position
                        try:
                            cable_path.save()
                        except Exception:
                            pass  # Duplicate path — already exists

            if rebuild:
                rebuild_paths(node)
            return

    # Standard cable or no breakout endpoint found — single path
    cable_path = CablePath.from_origin(node)
    if cable_path:
        try:
            cable_path.save()
        except Exception as e:
            print(node, node.pk)
            raise e
    if rebuild:
        rebuild_paths(node)


def rebuild_paths(obj):
    """
    Rebuild all CablePaths which traverse the specified node
    """
    cable_paths = CablePath.objects.filter(path__contains=obj)

    with transaction.atomic():
        for cp in cable_paths:
            cp.delete()
            # Prevent looping back to rebuild_paths during the atomic transaction.
            create_cablepath(cp.origin, rebuild=False)


#
# location/rack/device assignment
#


@receiver(post_save, sender=RackGroup)
def handle_rackgroup_location_change(instance, created, raw=False, **kwargs):
    """
    Update child RackGroups, Racks, and PowerPanels if Location assignment has changed.

    We intentionally recurse through each child object instead of calling update() on the QuerySet
    to ensure the proper change records get created for each.

    Note that this is non-trivial for Location changes, since a LocationType that can contain RackGroups
    may or may not be permitted to contain Racks or PowerPanels. If it's not permitted, rather than trying to search
    through child locations to find the "right" one, the best we can do is to raise to raise a ValidationError
    and roll back the changes we made.
    """
    if raw or created:
        return

    with transaction.atomic():
        descendants = instance.location.descendants(include_self=True)
        content_types = instance.location.location_type.content_types.all()
        rack_groups_permitted = ContentType.objects.get_for_model(RackGroup) in content_types
        racks_permitted = ContentType.objects.get_for_model(Rack) in content_types
        power_panels_permitted = ContentType.objects.get_for_model(PowerPanel) in content_types

        for rackgroup in instance.children.all():
            if rackgroup.location not in descendants:
                if not rack_groups_permitted:
                    raise ValidationError(
                        {
                            f"location {instance.location.name}": "RackGroups may not associate to locations of type "
                            f'"{instance.location.location_type}"'
                        }
                    )
                rackgroup.location = instance.location
                rackgroup.save()

        for rack in Rack.objects.filter(rack_group=instance):
            if rack.location not in descendants:
                if not racks_permitted:
                    raise ValidationError(
                        {
                            f"location {instance.location.name}": "Racks may not associate to locations of type "
                            f'"{instance.location.location_type}"'
                        }
                    )
                rack.location = instance.location
                rack.save()

        for powerpanel in PowerPanel.objects.filter(rack_group=instance):
            if powerpanel.location not in descendants:
                if not power_panels_permitted:
                    raise ValidationError(
                        {
                            f"location {instance.location.name}": "PowerPanels may not associate to locations of type "
                            f'"{instance.location.location_type}"'
                        }
                    )
                powerpanel.location = instance.location
                powerpanel.save()


@receiver(post_save, sender=Rack)
def handle_rack_location_change(instance, created, raw=False, **kwargs):
    """
    Update child Devices if Location assignment has changed.

    Note that this is non-trivial for Location changes, since a LocationType that can contain Racks
    may or may not be permitted to contain Devices. If it's not permitted, rather than trying to search
    through child locations to find the "right" one, the best we can do is to raise a ValidationError
    and roll back the changes we made.
    """
    if raw or created:
        return
    with transaction.atomic():
        devices_permitted = (
            ContentType.objects.get_for_model(Device) in instance.location.location_type.content_types.all()
        )

        for device in Device.objects.filter(rack=instance):
            if device.location != instance.location:
                if not devices_permitted:
                    raise ValidationError(
                        {
                            f"location {instance.location.name}": "Devices may not associate to locations of type "
                            f'"{instance.location.location_type}"'
                        }
                    )
                device.location = instance.location
                device.save()


#
# Device redundancy group
#


@receiver(pre_delete, sender=DeviceRedundancyGroup)
def clear_deviceredundancygroup_members(instance, **kwargs):
    """
    When a DeviceRedundancyGroup is deleted, nullify the device_redundancy_group_priority field of its prior members.
    """
    devices = Device.objects.filter(device_redundancy_group=instance.pk)
    for device in devices:
        device.device_redundancy_group_priority = None
        device.save()


#
# Virtual chassis
#


@receiver(post_save, sender=VirtualChassis)
def assign_virtualchassis_master(instance, created, raw=False, **kwargs):
    """
    When a VirtualChassis is created, automatically assign its master device (if any) to the VC.
    """
    if raw:
        return
    if created and instance.master:
        master = Device.objects.get(pk=instance.master.pk)
        master.virtual_chassis = instance
        if instance.master.vc_position is None:
            master.vc_position = 1
        master.save()


@receiver(pre_delete, sender=VirtualChassis)
def clear_virtualchassis_members(instance, **kwargs):
    """
    When a VirtualChassis is deleted, nullify the vc_position and vc_priority fields of its prior members.
    """
    devices = Device.objects.filter(virtual_chassis=instance.pk)
    for device in devices:
        device.vc_position = None
        device.vc_priority = None
        device.save()


#
# Cables
#


@receiver(post_save, sender=Cable)
def update_connected_endpoints(instance, created, raw=False, **kwargs):
    """
    When a Cable is saved, create CableTermination rows from initial terminations,
    sync cable/peer caches on termination objects, and create/update CablePaths.
    """
    logger = logging.getLogger(__name__ + ".cable")
    if raw:
        logger.debug(f"Skipping endpoint updates for imported cable {instance}")
        return

    # On creation, create CableTermination rows and sync caches
    if created:
        _create_cable_termination_rows(instance, logger)
        _sync_termination_caches(instance, logger)
        for ct_row in instance.terminations.all():
            term = ct_row.termination
            if isinstance(term, PathEndpoint):
                create_cablepath(term)
            else:
                rebuild_paths(term)
    elif instance.status != instance._orig_status:
        # Status changed — update path active flags or rebuild
        if instance.status != Cable.STATUS_CONNECTED:
            CablePath.objects.filter(path__contains=instance).update(is_active=False)
        else:
            rebuild_paths(instance)
    # NOTE: On regular updates (form save), we do NOT sync termination caches here.
    # The form's _save_connection_terminations() handles CableTermination row
    # creation/updates and cache syncing AFTER this signal runs.


def _create_cable_termination_rows(instance, logger):
    """Create CableTermination rows from the Cable's _initial_termination_a/b attributes."""
    term_a = getattr(instance, "_initial_termination_a", None)
    term_b = getattr(instance, "_initial_termination_b", None)

    # Also handle type/id kwargs for the case where termination objects aren't resolved yet
    if term_a is None and getattr(instance, "_initial_termination_a_type", None):
        ct = instance._initial_termination_a_type
        term_a = ct.model_class().objects.get(pk=instance._initial_termination_a_id)
    if term_b is None and getattr(instance, "_initial_termination_b_type", None):
        ct = instance._initial_termination_b_type
        term_b = ct.model_class().objects.get(pk=instance._initial_termination_b_id)

    # Determine lane 1 connector/position if this is a breakout cable
    a_connector = a_position = b_connector = b_position = None
    if instance.cable_type_id and instance.cable_type.mapping:
        entry = instance.cable_type.mapping[0]
        a_connector = entry["a_connector"]
        a_position = entry["a_position"]
        b_connector = entry["b_connector"]
        b_position = entry["b_position"]

    if term_a:
        ct_a = ContentType.objects.get_for_model(term_a)
        CableToCableTermination.objects.get_or_create(
            cable=instance,
            cable_end="A",
            termination_type=ct_a,
            termination_id=term_a.pk,
            defaults={"connector": a_connector, "position": a_position},
        )
        logger.debug(f"Created CableTermination A-side for {term_a} on cable {instance}")

    if term_b:
        ct_b = ContentType.objects.get_for_model(term_b)
        CableToCableTermination.objects.get_or_create(
            cable=instance,
            cable_end="B",
            termination_type=ct_b,
            termination_id=term_b.pk,
            defaults={"connector": b_connector, "position": b_position},
        )
        logger.debug(f"Created CableTermination B-side for {term_b} on cable {instance}")


def _sync_termination_caches(instance, logger):
    """Sync the `cable` FK on termination objects from the CableToCableTermination rows."""
    for endpoint in instance.terminations.all():
        termination = endpoint.termination
        if termination is None:
            continue
        if termination.cable_id != instance.pk:
            logger.debug(f"Syncing cable FK for {termination} on cable {instance}")
            termination.cable = instance
            termination.save()


@receiver(pre_delete, sender=Cable)
def nullify_connected_endpoints(instance, **kwargs):
    """
    When a Cable is deleted, clear cable/peer caches on all termination objects
    and retrace dependent cable paths.
    """
    logger = logging.getLogger(__name__ + ".cable")

    # Clear the cable FK on all termination objects
    for endpoint in instance.terminations.all():
        termination = endpoint.termination
        if termination is not None:
            logger.debug(f"Nullifying termination {termination} for cable {instance}")
            termination.cable = None
            termination.save()

    # CableToCableTermination rows will be CASCADE-deleted with the Cable.
    # Retrace any dependent cable paths.
    for cablepath in CablePath.objects.filter(path__contains=instance):
        cp = CablePath.from_origin(cablepath.origin)
        if cp:
            CablePath.objects.filter(pk=cablepath.pk).update(
                path=cp.path,
                destination_type=ContentType.objects.get_for_model(cp.destination) if cp.destination else None,
                destination_id=cp.destination.pk if cp.destination else None,
                is_active=cp.is_active,
                is_split=cp.is_split,
            )
        else:
            cablepath.delete()


#
# Termination object deletion — clean up CableToCableTermination without cascading to Cable
#


@functools.lru_cache(maxsize=1)
def _get_cable_termination_senders():
    from nautobot.circuits.models import CircuitTermination

    return [
        CircuitTermination,
        ConsolePort,
        ConsoleServerPort,
        FrontPort,
        Interface,
        PowerFeed,
        PowerOutlet,
        PowerPort,
        RearPort,
    ]


def handle_termination_delete(sender, instance, **kwargs):
    """
    When a termination object is deleted, remove its CableToCableTermination row
    and clean up caches. The Cable itself survives — it just loses this termination.
    """
    if not instance.cable_id:
        return

    logger = logging.getLogger(__name__ + ".cable")
    logger.debug(f"Handling termination delete for {instance} (cable: {instance.cable})")

    # Delete the CableToCableTermination row for this termination
    ct_type = ContentType.objects.get_for_model(instance)
    CableToCableTermination.objects.filter(
        termination_type=ct_type,
        termination_id=instance.pk,
    ).delete()

    # Rebuild CablePaths that passed through this cable
    try:
        cable = Cable.objects.get(pk=instance.cable_id)
        rebuild_paths(cable)
    except Cable.DoesNotExist:
        pass


for _sender in _get_cable_termination_senders():
    pre_delete.connect(handle_termination_delete, sender=_sender)


#
# Interface tagged VLAMs
#


@receiver(m2m_changed, sender=Interface.tagged_vlans.through)
@disable_for_loaddata
def prevent_adding_tagged_vlans_with_incorrect_mode_or_site(sender, instance, action, **kwargs):
    if action != "pre_add":
        return

    validate_interface_tagged_vlans(instance, kwargs["model"], kwargs["pk_set"])


#
# VirtualDeviceContext Interfaces
#


@receiver(m2m_changed, sender=InterfaceVDCAssignment)
@disable_for_loaddata
def validate_vdcs_interface_relationships(sender, instance, action, **kwargs):
    if action != "pre_add":
        return

    pk_set = kwargs.get("pk_set", [])
    if isinstance(instance, Interface):
        invalid_vdcs = kwargs["model"].objects.filter(pk__in=pk_set).exclude(device=instance.device)
        if invalid_vdcs.count():
            raise ValidationError(
                {
                    "virtual_device_contexts": (
                        f"Virtual Device Context with names {list(invalid_vdcs.values_list('name', flat=True))} must all belong to the "
                        f"same device as the interface's device."
                    )
                }
            )
    else:
        vc_interfaces_ids = instance.device.vc_interfaces.values_list("pk", flat=True)
        invalid_interfaces = (
            kwargs["model"]
            .objects.filter(pk__in=pk_set)
            .exclude(device=instance.device)
            .exclude(id__in=vc_interfaces_ids)
        )

        if invalid_interfaces.count():
            raise ValidationError(
                {
                    "interfaces": (
                        f"Interfaces with names {list(invalid_interfaces.values_list('name', flat=True))} must all belong to the "
                        f"same device as the Virtual Device Context's device."
                    )
                }
            )


#
# ControllerManagedDeviceGroup
#


@receiver(post_save, sender=ControllerManagedDeviceGroup)
def handle_controller_managed_device_group_controller_change(instance, raw=False, **_):
    """Update descendants when the top level `ControllerManagedDeviceGroup.controller` changes."""
    logger = logging.getLogger(__name__ + ".ControllerManagedDeviceGroup")

    if raw:
        logger.debug("Skipping controller update for imported controller device group %s", instance)
        return

    if instance.parent or instance._original_controller == instance.controller:
        return

    with transaction.atomic():
        for group in instance.descendants(include_self=False):
            group.controller = instance.controller
            group.save()
            logger.debug("Updated controller from parent %s for child %s", instance, group)


@receiver(m2m_changed, sender=LocationType.content_types.through)
def content_type_changed(instance, action, **kwargs):
    """
    Prevents removal of a ContentType from LocationType if it's in use by any models
    associated with the locations.
    """

    if action != "pre_remove":
        return

    removed_content_types = ContentType.objects.filter(pk__in=kwargs.get("pk_set", []))

    for content_type in removed_content_types:
        model_class = content_type.model_class()

        if model_class.objects.filter(location__location_type=instance).exists():
            raise ValidationError(
                {
                    "content_types": (
                        f"Cannot remove the content type {content_type} as currently at least one {model_class._meta.verbose_name} is associated to a location of this location type. "
                    )
                }
            )


#
# Device/Cluster assignments
#


@receiver(m2m_changed, sender=Device.clusters.through)
def ensure_device_and_cluster_locations_are_compatible(sender, instance, action, pk_set, **kwargs):
    """
    When adding clusters to a device, clean the added DeviceClusterAssignment records to enforce location compatibility.
    """
    if action == "post_add" and pk_set:
        if isinstance(instance, Device):
            for assignment in instance.cluster_assignments.filter(cluster_id__in=pk_set):
                assignment.clean()
        else:  # instance is a Cluster
            for assignment in instance.device_assignments.filter(device_id__in=pk_set):
                assignment.clean()
