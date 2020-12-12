from graphene_django import DjangoObjectType

from circuits.models import CircuitTermination
from circuits.filters import CircuitTerminationFilterSet
from dcim.graphql.types import CableTerminationMixin


class CircuitTerminationType(DjangoObjectType, CableTerminationMixin):
    """Graphql Type Object for CircuitTermination model."""
    class Meta:
        model = CircuitTermination
        filterset_class = CircuitTerminationFilterSet
