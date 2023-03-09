from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save, m2m_changed
from django.dispatch import receiver

from nautobot.ipam.models import Prefix, VRF


@receiver(pre_save, sender=Prefix)
@receiver(pre_save, sender=VRF)
@receiver(pre_save, sender=VRF.devices.through)
@receiver(pre_save, sender=VRF.prefixes.through)
def ipam_object_created(sender, instance, raw=False, **kwargs):
    """
    Forcibly call `full_clean()` when a new IPAM object
    is manually created to prevent inadvertantly creating invalid objects.
    """
    if raw:
        return
    instance.full_clean()


@receiver(m2m_changed, sender=VRF.prefixes.through)
def vrf_prefix_associated(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Disallow adding Prefixes if the namespace doesn't match.
    """

    if action == "pre_add":
        prefixes = model.objects.filter(pk__in=pk_set).exclude(namespace=instance.namespace)
        if prefixes.exists():
            raise ValidationError({"prefixes": "Prefix must match namespace of VRF"})
