from nautobot.core.graphql.base import NautobotObjectType
from nautobot.circuits.models import CircuitTermination
from nautobot.circuits.filters import CircuitTerminationFilterSet
from nautobot.dcim.graphql.mixins import PathEndpointMixin


class CircuitTerminationType(NautobotObjectType, PathEndpointMixin):
    """Graphql Type Object for CircuitTermination model."""

    class Meta:
        model = CircuitTermination
        filterset_class = CircuitTerminationFilterSet
