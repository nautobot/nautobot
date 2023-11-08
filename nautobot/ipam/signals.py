from django.db.models.signals import pre_save
from django.dispatch import receiver

from nautobot.ipam.models import IPAddress


@receiver(pre_save, sender=IPAddress)
def add_broadcast_to_ipaddress_if_not_provided(instance, **kwargs):
    if not instance.broadcast:
        broadcast = instance.get_broadcast(instance.address)
        instance.broadcast = broadcast


