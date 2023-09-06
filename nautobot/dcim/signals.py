import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.db import transaction
from django.dispatch import receiver

from nautobot.core.signals import disable_for_loaddata
from .models import (
    Cable,
    CablePath,
    Device,
    PathEndpoint,
    PowerPanel,
    Rack,
    RackGroup,
    VirtualChassis,
    Interface,
)
from .utils import validate_interface_tagged_vlans


def create_cablepath(node, rebuild=True):
    """
    Create CablePaths for all paths originating from the specified node.

    rebuild (bool) - Used to refresh paths where this node is not an endpoint.
    """
    cp = CablePath.from_origin(node)
    if cp:
        try:
            cp.save()
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
    When a Cable is saved, check for and update its two connected endpoints
    """
    logger = logging.getLogger(__name__ + ".cable")
    if raw:
        logger.debug(f"Skipping endpoint updates for imported cable {instance}")
        return

    # Cache the Cable on its two termination points
    if instance.termination_a.cable != instance:
        logger.debug(f"Updating termination A for cable {instance}")
        instance.termination_a.cable = instance
        instance.termination_a._cable_peer = instance.termination_b
        instance.termination_a.save()
    if instance.termination_b.cable != instance:
        logger.debug(f"Updating termination B for cable {instance}")
        instance.termination_b.cable = instance
        instance.termination_b._cable_peer = instance.termination_a
        instance.termination_b.save()

    # Create/update cable paths
    if created:
        for termination in (instance.termination_a, instance.termination_b):
            if isinstance(termination, PathEndpoint):
                create_cablepath(termination)
            else:
                rebuild_paths(termination)
    elif instance.status != instance._orig_status:
        # We currently don't support modifying either termination of an existing Cable. (This
        # may change in the future.) However, we do need to capture status changes and update
        # any CablePaths accordingly.
        if instance.status != Cable.STATUS_CONNECTED:
            CablePath.objects.filter(path__contains=instance).update(is_active=False)
        else:
            rebuild_paths(instance)


@receiver(pre_delete, sender=Cable)
def nullify_connected_endpoints(instance, **kwargs):
    """
    When a Cable is deleted, check for and update its two connected endpoints
    """
    logger = logging.getLogger(__name__ + ".cable")

    # Disassociate the Cable from its termination points
    if instance.termination_a is not None:
        logger.debug(f"Nullifying termination A for cable {instance}")
        instance.termination_a.cable = None
        instance.termination_a._cable_peer = None
        instance.termination_a.save()
    if instance.termination_b is not None:
        logger.debug(f"Nullifying termination B for cable {instance}")
        instance.termination_b.cable = None
        instance.termination_b._cable_peer = None
        instance.termination_b.save()

    # Delete and retrace any dependent cable paths
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
# Interface tagged VLAMs
#


@receiver(m2m_changed, sender=Interface.tagged_vlans.through)
@disable_for_loaddata
def prevent_adding_tagged_vlans_with_incorrect_mode_or_site(sender, instance, action, **kwargs):
    if action != "pre_add":
        return

    validate_interface_tagged_vlans(instance, kwargs["model"], kwargs["pk_set"])
