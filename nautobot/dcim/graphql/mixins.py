import graphene

# from nautobot.dcim.graphql.types import InterfaceType


class CablePeerEndpointMixin:
    """Mixin for GraphQL objects that act as CablePeerEndpoints"""

    cable_peer_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    cable_peer_console_port = graphene.Field("nautobot.dcim.graphql.types.ConsolePortType")
    cable_peer_console_server_port = graphene.Field("nautobot.dcim.graphql.types.ConsoleServerPortType")
    cable_peer_front_port = graphene.Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")
    cable_peer_power_feed = graphene.Field("nautobot.dcim.graphql.types.PowerFeedType")
    cable_peer_power_outlet = graphene.Field("nautobot.dcim.graphql.types.PowerOutletType")
    cable_peer_power_port = graphene.Field("nautobot.dcim.graphql.types.PowerPortType")
    cable_peer_rear_port = graphene.Field("nautobot.dcim.graphql.types.RearPortType")

    def resolve_cable_peer_circuit_termination(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "CircuitTermination":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_cable_peer_console_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "ConsolePort":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_cable_peer_console_server_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "ConsoleServerPort":  # type built-in used to avoid class loading
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

    def resolve_cable_peer_power_feed(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "PowerFeed":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_cable_peer_power_outlet(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "PowerOutlet":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_cable_peer_power_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "PowerPort":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_cable_peer_rear_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "RearPort":  # type built-in used to avoid class loading
            return peer
        return None


class PathEndpointMixin:
    """Mixin for GraphQL objects that act as PathEndpoints."""

    connected_endpoint = graphene.Field("nautobot.dcim.graphql.types.CableTerminationTypes")
    path = graphene.Field("nautobot.dcim.graphql.types.CablePathType")

    connected_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    connected_console_port = graphene.Field("nautobot.dcim.graphql.types.ConsolePortType")
    connected_console_server_port = graphene.Field("nautobot.dcim.graphql.types.ConsoleServerPortType")
    connected_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")
    connected_power_feed = graphene.Field("nautobot.dcim.graphql.types.PowerFeedType")
    connected_power_outlet = graphene.Field("nautobot.dcim.graphql.types.PowerOutletType")
    connected_power_port = graphene.Field("nautobot.dcim.graphql.types.PowerPortType")

    def resolve_connected_circuit_termination(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "CircuitTermination":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_console_port(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "ConsolePort":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_console_server_port(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "ConsoleServerPort":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_interface(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "Interface":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_power_feed(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "PowerFeed":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_power_outlet(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "PowerOutlet":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_power_port(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "PowerPort":  # type built-in used to avoid class loading
            return peer
        return None
