from cacheops import invalidate_obj
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Circuit, CircuitTermination
from nautobot.dcim.models import CablePath
from nautobot.dcim.signals import create_cablepath


def rebuild_paths_circuits(obj):
    """
    Rebuild all CablePaths which traverse, begin or end with the specified node.
    """
    termination_type = ContentType.objects.get_for_model(CircuitTermination)

    cable_paths = CablePath.objects.filter(
        Q(path__contains=obj)
        | Q(destination_type=termination_type, destination_id=obj.pk)
        | Q(origin_type=termination_type, origin_id=obj.pk)
    )

    with transaction.atomic():
        for cp in cable_paths:
            invalidate_obj(cp.origin)
            cp.delete()
            # Prevent looping back to rebuild_paths during the atomic transaction.
            create_cablepath(cp.origin, rebuild=False)


@receiver((post_save, post_delete), sender=CircuitTermination)
def update_circuit(instance, **kwargs):
    """
    When a CircuitTermination has been modified, update the last_updated time of its parent Circuit.
    """
    circuits = Circuit.objects.filter(pk=instance.circuit_id)
    time = timezone.now()
    for circuit in circuits:
        circuit.last_updated = time
        circuit.save()


@receiver(post_save, sender=CircuitTermination)
def update_connected_terminations(instance, **kwargs):
    """
    When a CircuitTermination has been modified, update the Cable Paths if the Circuit Termination has a peer.
    """
    peer = instance.get_peer_termination()
    # Check if Circuit Termination has a peer
    if peer:
        rebuild_paths_circuits(peer)
