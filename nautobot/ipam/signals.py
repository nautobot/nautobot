from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save, m2m_changed
from django.dispatch import receiver

from nautobot.ipam.models import VRF, VRFDeviceAssignment, VRFPrefixAssignment


@receiver(pre_save, sender=VRFDeviceAssignment)
@receiver(pre_save, sender=VRFPrefixAssignment)
def ipam_object_saved(sender, instance, raw=False, **kwargs):
    """
    Forcibly call `full_clean()` when a new IPAM intermediate model is manually saved to prevent
    creation of invalid objects.
    """
    if raw:
        return
    instance.full_clean()


@receiver(m2m_changed, sender=VRFPrefixAssignment)
def vrf_prefix_associated(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Disallow adding Prefixes if the namespace doesn't match.
    """

    if action == "pre_add":
        prefixes = model.objects.filter(pk__in=pk_set).exclude(namespace=instance.namespace)
        if prefixes.exists():
            raise ValidationError({"prefixes": "Prefix must match namespace of VRF"})


@receiver(m2m_changed, sender=VRFDeviceAssignment)
def vrf_device_associated(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Assert validation on m2m when devices are associated with a VRF.
    """

    # TODO(jathan): Temporary workaround until a formset to add/remove/update VRFs <-> Devices and
    # optionally setting RD/name on assignment. k
    if action == "post_add":
        if isinstance(instance, VRF):
            for assignment in instance.device_assignments.iterator():
                assignment.validated_save()
        else:
            for assignment in instance.vrf_assignments.iterator():
                assignment.validated_save()
