from graphene import Field
import graphene_django_optimizer as gql_optimizer

from nautobot.core.graphql.utils import construct_resolver
from nautobot.circuits.models import CircuitTermination
from nautobot.circuits.filters import CircuitTerminationFilterSet
from nautobot.dcim.graphql.mixins import CableTerminationMixin, PathEndpointMixin


class CircuitTerminationType(gql_optimizer.OptimizedDjangoObjectType, CableTerminationMixin, PathEndpointMixin):
    """Graphql Type Object for CircuitTermination model."""

    class Meta:
        model = CircuitTermination
        filterset_class = CircuitTerminationFilterSet

    cable_peer_circuit_termination = Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    cable_peer_front_port = Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_interface = Field("nautobot.dcim.graphql.types.InterfaceType")
    cable_peer_rear_port = Field("nautobot.dcim.graphql.types.RearPortType")
    connected_circuit_termination = Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    connected_interface = Field("nautobot.dcim.graphql.types.InterfaceType")

    resolve_cable_peer_circuit_termination = construct_resolver("CircuitTermination", "cable_peer")
    resolve_cable_peer_front_port = construct_resolver("FrontPort", "cable_peer")
    resolve_cable_peer_interface = construct_resolver("Interface", "cable_peer")
    resolve_cable_rear_port = construct_resolver("RearPort", "cable_peer")
    resolve_connected_circuit_termination = construct_resolver("CircuitTermination", "connected_endpoint")
    resolve_connected_interface = construct_resolver("Interface", "connected_endpoint")
