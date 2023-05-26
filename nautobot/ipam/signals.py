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
        int_or_vm_int = instance.interface
        other_assignments_exist = (
            IPAddressToInterface.objects.filter(interface__device=host, ip_address=instance.ip_address)
            .exclude(id=instance.id)
            .exists()
        )
        model_name = "Device"
    else:
        host = instance.vm_interface.virtual_machine
        int_or_vm_int = instance.vm_interface
        other_assignments_exist = (
            IPAddressToInterface.objects.filter(vm_interface__virtual_machine=host, ip_address=instance.ip_address)
            .exclude(id=instance.id)
            .exists()
        )
        model_name = "Virtual Machine"

    ip_address = instance.ip_address
    # IP address validation
    if host:
        if host.primary_ip4 and host.primary_ip4 == ip_address and not other_assignments_exist:
            raise ValidationError(
                {
                    "ip_addresses": f"Cannot remove IP address {ip_address} from interface {int_or_vm_int} on {model_name} {host} because it is marked as its primary IPv{ip_address.family} address"
                }
            )
        if host.primary_ip6 and host.primary_ip6 == ip_address and not other_assignments_exist:
            raise ValidationError(
                {
                    "ip_addresses": f"Cannot remove IP address {ip_address} from interface {int_or_vm_int} on {model_name} {host} because it is marked as its primary IPv{ip_address.family} address"
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
