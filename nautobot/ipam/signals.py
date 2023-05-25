from django.core.exceptions import ValidationError
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from nautobot.ipam.models import IPAddressToInterface


@receiver(pre_delete, sender=IPAddressToInterface)
def ip_address_to_interface_pre_delete_validation(instance, raw=False, **kwargs):
    if raw:
        return

    # Check if the removed IPAddressToInterface instance contains an IPAddress
    # that is the primary_v{version} of the host machine.

    if getattr(instance, "interface"):
        host = instance.interface.device
        model_name = "Device"
    else:
        host = instance.vm_interface.virtual_machine
        model_name = "Virtual Machine"

    ip_address = instance.ip_address
    # IP address validation
    if host:
        if host.primary_ip4 and host.primary_ip4 == ip_address:
            raise ValidationError(
                {
                    "ip_addresses": f"IP address {host.primary_ip4} is primary for {model_name} {host} but not assigned to it!"
                }
            )
        if host.primary_ip6 and host.primary_ip6 == ip_address:
            raise ValidationError(
                {
                    "ip_addresses": f"IP address {host.primary_ip6} is primary for {model_name} {host} but not assigned to it!"
                }
            )


@receiver(pre_save, sender=IPAddressToInterface)
def ip_address_to_interface_assignment_created(sender, instance, raw=False, **kwargs):
    """
    Forcibly call `full_clean()` when a new `IPAddressToInterface` object
    is manually created to prevent inadvertantly creating invalid IPAddressToInterface.
    """
    if raw:
        return

    instance.full_clean()
