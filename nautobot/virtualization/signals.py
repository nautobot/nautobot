from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.virtualization.models import VMInterface


#
# VMInterface tagged VLAMs
#


@receiver(m2m_changed, sender=VMInterface.tagged_vlans.through)
def prevent_adding_tagged_vlans_if_mode_not_set_to_tagged(sender, instance, action, **kwargs):
    if action != "pre_add":
        return

    if instance.mode != InterfaceModeChoices.MODE_TAGGED:
        raise ValidationError(
            {"tagged_vlans": f"Mode must be set to {InterfaceModeChoices.MODE_TAGGED} when specifying tagged_vlans"}
        )
