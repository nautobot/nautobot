import graphene


class PathEndpointMixin:
    """Mixin for GraphQL objects that act as PathEndpoints."""

    connected_endpoint = graphene.Field("nautobot.dcim.graphql.types.CableTerminationTypes")
    path = graphene.Field("nautobot.dcim.graphql.types.CablePathType")

    connected_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")
    connected_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    connected_console_server_port = graphene.Field("nautobot.dcim.graphql.types.ConsoleServerPortType")

    def resolve_connected_interface(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "Interface":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_circuit_termination(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "CircuitTermination":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_console_server_port(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "ConsoleServerPort":  # type built-in used to avoid class loading
            return peer
        return None
