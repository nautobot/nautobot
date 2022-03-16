from graphene import Field
import graphene_django_optimizer as gql_optimizer

from nautobot.circuits.models import CircuitTermination
from nautobot.circuits.filters import CircuitTerminationFilterSet
from nautobot.dcim.graphql.mixins import PathEndpointMixin


class CircuitTerminationType(gql_optimizer.OptimizedDjangoObjectType, PathEndpointMixin):
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

    def resolve_cable_peer_circuit_termination(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "CircuitTermination":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_cable_peer_front_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "FrontPort":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_cable_peer_interface(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "Interface":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_cable_peer_rear_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "RearPort":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_circuit_termination(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "CircuitTermination":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_interface(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "Interface":  # type built-in used to avoid class loading
            return peer
        return None
