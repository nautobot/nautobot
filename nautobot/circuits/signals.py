from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from nautobot.dcim.models import CablePath
from nautobot.dcim.signals import create_cablepath

from .choices import CircuitTerminationSideChoices
from .models import CircuitTermination


def rebuild_paths_circuits(obj):
    """
    Rebuild all CablePaths which traverse, begin or end with the specified node.
    """
    termination_type = ContentType.objects.get_for_model(CircuitTermination)

    # TODO: Remove pylint disable after issue is resolved (see: https://github.com/PyCQA/pylint/issues/7381)
    # pylint: disable=unsupported-binary-operation
    cable_paths = CablePath.objects.filter(
        Q(path__contains=obj)
        | Q(destination_type=termination_type, destination_id=obj.pk)
        | Q(origin_type=termination_type, origin_id=obj.pk)
    )
    # pylint: enable=unsupported-binary-operation

    with transaction.atomic():
        for cp in cable_paths:
            cp.delete()
            # Prevent looping back to rebuild_paths during the atomic transaction.
            create_cablepath(cp.origin, rebuild=False)


@receiver(post_save, sender=CircuitTermination)
def update_circuit(instance, raw=False, **kwargs):
    """
    When a CircuitTermination has been modified, update its parent Circuit.
    """
    if raw:
        return
    if instance.term_side in CircuitTerminationSideChoices.values():
        termination_name = f"circuit_termination_{instance.term_side.lower()}"
        setattr(instance.circuit, termination_name, instance)
        setattr(instance.circuit, "last_updated", timezone.now())
        instance.circuit.save()


@receiver(post_save, sender=CircuitTermination)
def update_connected_terminations(instance, raw=False, **kwargs):
    """
    When a CircuitTermination has been modified, update the Cable Paths if the Circuit Termination has a peer.
    """
    if raw:
        return
    peer = instance.get_peer_termination()
    # Check if Circuit Termination has a peer
    if peer:
        rebuild_paths_circuits(peer)
