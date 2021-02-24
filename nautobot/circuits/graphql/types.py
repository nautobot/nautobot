from graphene_django import DjangoObjectType

from nautobot.circuits.models import CircuitTermination
from nautobot.circuits.filters import CircuitTerminationFilterSet
from nautobot.dcim.graphql.types import CableTerminationMixin


class CircuitTerminationType(DjangoObjectType, CableTerminationMixin):
    """Graphql Type Object for CircuitTermination model."""

    class Meta:
        model = CircuitTermination
        filterset_class = CircuitTerminationFilterSet
