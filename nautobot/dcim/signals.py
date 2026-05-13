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
    my_endpoint = getattr(node, "cable_termination", None)
    if my_endpoint is None:
        if rebuild:
            rebuild_paths(node)
        return

    cable = my_endpoint.cable

    # Breakout cable: fan out one CablePath per distinct peer-side connector mapped from this
    # origin's connector. Multiple mapping entries that share a peer-side connector represent
    # internal lanes terminating at the same far-end object, so they collapse to one path.
    if cable.cable_type_id and my_endpoint.connector is not None:
        origin_side_key = "a_connector" if my_endpoint.cable_end == "A" else "b_connector"
        peer_side_key = "b_connector" if my_endpoint.cable_end == "A" else "a_connector"

        seen_peer_connectors = set()
        for mapping_entry in cable.cable_type.mapping:
            if mapping_entry[origin_side_key] != my_endpoint.connector:
                continue
            peer_connector = mapping_entry[peer_side_key]
            if peer_connector in seen_peer_connectors:
                continue
            seen_peer_connectors.add(peer_connector)

            cable_path = CablePath.from_origin(node, peer_connector=peer_connector)
            if cable_path is None:
                continue
            # Guard against re-entry: a parallel signal path (e.g. two `rebuild_paths` calls
            # landing on the same origin) may have already inserted the row for this
            # (origin, peer_connector). Check before saving so unrelated save failures still
            # propagate instead of being swallowed by a catch-all.
            already_exists = CablePath.objects.filter(
                origin_type_id=cable_path.origin_type_id,
                origin_id=cable_path.origin_id,
                peer_connector=peer_connector,
            ).exists()
            if not already_exists:
                cable_path.save()

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
    Rebuild all CablePaths which traverse the specified node.

    When `obj` is a `Cable`, origins are sourced from the cable's *current* terminations — so
    newly-added join rows are picked up and stale paths from removed join rows get replaced.
    For any other node (a termination or pass-through), origins are derived from the paths
    currently traversing it, since the node itself doesn't enumerate path origins.

    Origins are deduplicated because a single PathEndpoint owns multiple CablePaths on breakout
    cables (one per lane); `create_cablepath` is breakout-aware and rebuilds all of an origin's
    lane paths in a single call, so calling it once per origin is both sufficient and necessary.
    """
    cable_paths = CablePath.objects.filter(path__contains=obj)

    with transaction.atomic():
        # Always include origins of existing paths through `obj` so paths whose origin lives on
        # a *different* cable (e.g. an interface on the far side of a pass-through chain) get
        # rebuilt too.
        origins = [cp.origin for cp in cable_paths]
        if isinstance(obj, Cable):
            # Also include current PathEndpoint terminations on this cable so newly-added join
            # rows that don't yet have a CablePath get one built.
            origins.extend(
                ct_row.termination for ct_row in obj.terminations.all() if isinstance(ct_row.termination, PathEndpoint)
            )

        cable_paths.delete()

        seen = set()
        for origin in origins:
            if origin is None:
                continue
            key = (type(origin), origin.pk)
            if key in seen:
                continue
            seen.add(key)
            # `rebuild=False` prevents looping back into `rebuild_paths` during this atomic block.
            create_cablepath(origin, rebuild=False)


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


@receiver(pre_delete, sender=Cable)
def nullify_connected_endpoints(instance, **kwargs):
    """
    When a Cable is deleted, retrace dependent cable paths.

    Removes this cable's join-table rows up front so that path-retrace logic sees each affected
    termination as no-longer-connected; otherwise `from_origin` would still find the (about-to-be-
    deleted) cable in the DB. The Cable.delete() that triggered this signal would CASCADE-remove
    these rows anyway — we just bring it forward.
    """
    instance.terminations.all().delete()

    for cablepath in CablePath.objects.filter(path__contains=instance):
        cp = CablePath.from_origin(cablepath.origin, peer_connector=cablepath.peer_connector)
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
    When a termination object is deleted, retrace cable paths on the connected cable (if any).

    The CableToCableTermination row pointing at this termination is CASCADE-deleted automatically
    via the per-type OneToOneField; the Cable itself survives.
    """
    cable_termination = getattr(instance, "cable_termination", None)
    if cable_termination is None:
        return

    logger = logging.getLogger(__name__ + ".cable")
    cable = cable_termination.cable
    logger.debug(f"Handling termination delete for {instance} (cable: {cable})")
    rebuild_paths(cable)


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
