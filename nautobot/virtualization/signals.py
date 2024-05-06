from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from nautobot.dcim.utils import validate_interface_tagged_vlans
from nautobot.virtualization.models import VMInterface

#
# VMInterface tagged VLAMs
#


@receiver(m2m_changed, sender=VMInterface.tagged_vlans.through)
def prevent_adding_tagged_vlans_with_incorrect_mode_or_site(sender, instance, action, **kwargs):
    if action != "pre_add":
        return

    validate_interface_tagged_vlans(instance, kwargs["model"], kwargs["pk_set"])
