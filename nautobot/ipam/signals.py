from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save, m2m_changed

from nautobot.ipam.models import Prefix, VRF, VRFDeviceAssignment, VRFPrefixAssignment


def ipam_object_created(sender, instance, raw=False, **kwargs):
    """
    Forcibly call `full_clean()` when a new IPAM object
    is manually created to prevent inadvertantly creating invalid objects.
    """
    if raw:
        return
    instance.full_clean()


pre_save.connect(ipam_object_created, sender=Prefix)
pre_save.connect(ipam_object_created, sender=VRF)
pre_save.connect(ipam_object_created, sender=VRFDeviceAssignment)
pre_save.connect(ipam_object_created, sender=VRFPrefixAssignment)


def vrf_prefix_associated(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Disallow adding Prefixes if the namespace doesn't match.
    """

    if action == "pre_add":
        prefixes = model.objects.filter(pk__in=pk_set).exclude(namespace=instance.namespace)
        if prefixes.exists():
            raise ValidationError({"prefixes": "Prefix must match namespace of VRF"})


m2m_changed.connect(vrf_prefix_associated, sender=VRF.prefixes.through)
