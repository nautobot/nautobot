import graphene_django_optimizer as gql_optimizer

from nautobot.circuits.models import CircuitTermination
from nautobot.circuits.filters import CircuitTerminationFilterSet
from nautobot.dcim.graphql.mixins import PathEndpointMixin


class CircuitTerminationType(gql_optimizer.OptimizedDjangoObjectType, PathEndpointMixin):
    """Graphql Type Object for CircuitTermination model."""

    class Meta:
        model = CircuitTermination
        filterset_class = CircuitTerminationFilterSet
