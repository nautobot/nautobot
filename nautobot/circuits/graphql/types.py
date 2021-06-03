from graphene_django import DjangoObjectType

from nautobot.circuits.models import CircuitTermination
from nautobot.circuits.filters import CircuitTerminationFilterSet
from nautobot.dcim.graphql.mixins import PathEndpointMixin


class CircuitTerminationType(DjangoObjectType, PathEndpointMixin):
    """Graphql Type Object for CircuitTermination model."""

    class Meta:
        model = CircuitTermination
        filterset_class = CircuitTerminationFilterSet
