import contextlib
import logging
import threading

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete
from django.dispatch import receiver

from nautobot.core.signals import disable_for_loaddata

from .models import (
    Cable,
    CablePath,
    CableToCableTermination,
    ControllerManagedDeviceGroup,
    Device,
    DeviceRedundancyGroup,
    Interface,
    InterfaceVDCAssignment,
    LocationType,
    PathEndpoint,
    PowerPanel,
    Rack,
    RackGroup,
    VirtualChassis,
)
from .models.device_components import CableTermination
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
    if cable.cable_type_id and cable.cable_type.is_breakout:
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
    Rebuild all CablePaths affected by a change to the specified path node.

    Accepted input types and how each is interpreted:

    - **`Cable`** — rebuild every path that touches this cable. Origins are collected from
      three sources:
        * Existing CablePaths whose `path` JSON contains the cable.
        * Existing CablePaths whose `path` JSON contains any termination on the cable (catches
          partial paths that end *at* a termination but don't yet cross the cable — needed
          when a newly-added cable extends a previously-stranded path).
        * The cable's PathEndpoint terminations themselves (seeds for newly-cabled
          terminations that don't yet have any path row).
      All affected paths are deleted and rebuilt from the collected origins.
    - **`CableToCableTermination`** — resolved to its parent cable; same semantics as `Cable`.
      Used by the `post_save`/`post_delete` signal handlers on the join model so any row
      change (form, REST API, ORM, shell, job) automatically refreshes affected paths.
    - **`CableTermination` subclass** (Interface, ConsolePort, FrontPort, RearPort, PowerFeed,
      PowerOutlet, PowerPort, ConsoleServerPort, CircuitTermination) — rebuild only paths
      currently *traversing* this node, using each path's existing origin. No fresh origin
      seeding from the cable's other terminations, since the caller is signaling "this
      specific node was touched" rather than "this whole cable was touched." Useful when
      something happens to a termination that doesn't (yet) involve modifying any
      CableToCableTermination row.

    Any other input type raises `TypeError`. Origins are deduplicated; `create_cablepath` is
    breakout-aware and rebuilds all of an origin's lane paths in a single call.

    Most callers don't need to invoke this directly — modifying a `CableToCableTermination`
    row via any code path triggers it automatically via the signal handlers. For bulk row
    changes, wrap in `defer_cable_path_rebuilds()` to coalesce per-row rebuilds.
    """
    # Resolve CableToCableTermination → its cable (use Cable semantics from there).
    if isinstance(obj, CableToCableTermination):
        cable = Cable.objects.filter(pk=obj.cable_id).first()
        if cable is None:
            return
        obj = cable
    elif not isinstance(obj, (Cable, CableTermination)):
        raise TypeError(
            f"rebuild_paths() expects a Cable, CableToCableTermination, or CableTermination "
            f"subclass; got {type(obj).__name__}"
        )

    with transaction.atomic():
        # Always include origins of existing paths through `obj` so paths whose origin lives on
        # a *different* cable (e.g. an interface on the far side of a pass-through chain) get
        # rebuilt too.
        origins = [cp.origin for cp in CablePath.objects.filter(path__contains=obj)]
        CablePath.objects.filter(path__contains=obj).delete()

        if isinstance(obj, Cable):
            # Expand to paths that touch any termination on this cable — not just paths that
            # contain the cable itself. Two cases:
            #   1. Pass-throughs (FrontPort/RearPort) can sit mid-path; a path originating on
            #      another cable may end (or pass through) a pass-through on this cable.
            #   2. PathEndpoints on this cable may also be the dead-end of a partial path that
            #      originated elsewhere (e.g. a CircuitTermination connected via cable1 with no
            #      far-side path yet — when we add cable2 to its other side, that partial path
            #      needs to be re-traced to complete it).
            # In both cases, seed the upstream origin and delete the now-stale path so the
            # rebuild can re-trace through this cable's new state.
            for ct_row in obj.terminations.all():
                term = ct_row.termination
                if term is None:
                    continue
                affected = CablePath.objects.filter(path__contains=term)
                origins.extend(cp.origin for cp in affected)
                affected.delete()
                # Also seed PathEndpoint terminations themselves as fresh origins — newly-added
                # join rows that don't yet have a CablePath get one built.
                if isinstance(term, PathEndpoint):
                    origins.append(term)

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


# CableToCableTermination → CablePath auto-rebuild plumbing
#
# Any row INSERT/UPDATE/DELETE on the join table triggers a `rebuild_paths(cable)` for the affected
# cable, via the signal handler below. ORM/REST/form/job/shell callers all get path rebuilds for
# free without remembering to call `rebuild_paths` themselves.
#
# Bulk row-replacement flows (e.g. CableForm._save_connection_terminations, REST API termination
# updates) can use the `defer_cable_path_rebuilds()` context manager to coalesce per-row signal
# fires into a single per-cable flush at context exit. Not a public-facing API — apps doing
# normal one-off ORM modifications don't need it.

_batch_state = threading.local()


def _batching_active():
    return getattr(_batch_state, "depth", 0) > 0


@contextlib.contextmanager
def defer_cable_path_rebuilds():
    """Coalesce CableToCableTermination signal-driven path rebuilds into one flush per affected
    cable at context exit.

    Use around bulk row-replacement flows to avoid the per-row rebuild cost. Outside this
    context, every row change still triggers an immediate rebuild. Nestable: nested entries
    share the dirty set, and only the outermost exit fires flushes.
    """
    _batch_state.depth = getattr(_batch_state, "depth", 0) + 1
    if _batch_state.depth == 1:
        _batch_state.dirty_cables = set()
    try:
        yield
    finally:
        _batch_state.depth -= 1
        if _batch_state.depth == 0:
            dirty = _batch_state.dirty_cables
            _batch_state.dirty_cables = set()
            for cable_id in dirty:
                cable = Cable.objects.filter(pk=cable_id).first()
                if cable is not None:
                    rebuild_paths(cable)


@receiver(post_save, sender=CableToCableTermination)
@receiver(post_delete, sender=CableToCableTermination)
def _rebuild_paths_on_join_change(sender, instance, **kwargs):
    """Rebuild affected CablePaths when a CableToCableTermination row changes.

    Within a `defer_cable_path_rebuilds()` block, just record the cable as dirty; the outer
    context flushes once on exit.
    """
    cable_id = instance.cable_id
    if cable_id is None:
        return
    if _batching_active():
        _batch_state.dirty_cables.add(cable_id)
    else:
        cable = Cable.objects.filter(pk=cable_id).first()
        if cable is not None:
            rebuild_paths(cable)


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


# Cable deletion handling is now driven entirely by the `CableToCableTermination` post_delete
# signal: the cascade-delete fires `_rebuild_paths_on_join_change` for each join row, which
# rebuilds the affected paths. No bespoke Cable pre_delete handler is needed.


# Termination object deletion is handled implicitly: deleting an Interface (or any other
# CableTermination subclass) CASCADE-deletes the join row via its OneToOneField, which fires
# `_rebuild_paths_on_join_change` to rebuild the affected paths. The Cable itself survives.

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
