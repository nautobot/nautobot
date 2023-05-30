from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from nautobot.ipam.models import IPAddressToInterface


@receiver(pre_delete, sender=IPAddressToInterface)
def ip_address_to_interface_pre_delete(instance, raw=False, **kwargs):
    if raw:
        return

    # Check if the removed IPAddressToInterface instance contains an IPAddress
    # that is the primary_v{version} of the host machine.

    if getattr(instance, "interface"):
        host = instance.interface.device
    else:
        host = instance.vm_interface.virtual_machine

    if instance.ip_address == host.primary_ip4:
        host.primary_ip4 = None
    elif instance.ip_address == host.primary_ip6:
        host.primary_ip6 = None
    host.save()


@receiver(pre_save, sender=IPAddressToInterface)
def ip_address_to_interface_assignment_created(sender, instance, raw=False, **kwargs):
    """
    Forcibly call `full_clean()` when a new `IPAddressToInterface` object
    is manually created to prevent inadvertantly creating invalid IPAddressToInterface.
    """
    if raw:
        return

    instance.full_clean()
