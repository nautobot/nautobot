import graphene
import graphene_django_optimizer as gql_optimizer

from nautobot.circuits.graphql.types import CircuitTerminationType
from nautobot.dcim.graphql.mixins import PathEndpointMixin
from nautobot.dcim.models import (
    Cable,
    CablePath,
    ConsolePort,
    ConsoleServerPort,
    Device,
    FrontPort,
    Interface,
    PowerFeed,
    PowerOutlet,
    PowerPort,
    Rack,
    RearPort,
    Site,
)
from nautobot.dcim.filters import (
    CableFilterSet,
    ConsoleServerPortFilterSet,
    ConsolePortFilterSet,
    DeviceFilterSet,
    FrontPortFilterSet,
    InterfaceFilterSet,
    PowerFeedFilterSet,
    PowerOutletFilterSet,
    PowerPortFilterSet,
    RackFilterSet,
    RearPortFilterSet,
    SiteFilterSet,
)
from nautobot.extras.graphql.types import TagType  # noqa: F401


class SiteType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for Site model."""

    class Meta:
        model = Site
        filterset_class = SiteFilterSet
        exclude = ["images", "_name"]


class DeviceType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for Device model."""

    class Meta:
        model = Device
        filterset_class = DeviceFilterSet
        exclude = ["_name"]


class RackType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for Rack model."""

    class Meta:
        model = Rack
        filterset_class = RackFilterSet
        exclude = ["images"]


class CableType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for Cable model."""

    class Meta:
        model = Cable
        filterset_class = CableFilterSet
        exclude = ["_termination_a_device", "_termination_b_device"]

    termination_a_type = graphene.String()
    termination_b_type = graphene.String()

    def resolve_termination_a_type(self, args):
        if self.termination_a_type:
            model = self.termination_a_type.model_class()
            return f"{model._meta.app_label}.{model._meta.model_name}"
        return None

    def resolve_termination_b_type(self, args):
        if self.termination_b_type:
            model = self.termination_b_type.model_class()
            return f"{model._meta.app_label}.{model._meta.model_name}"
        return None


class CablePathType(gql_optimizer.OptimizedDjangoObjectType):
    """GraphQL type object for CablePath model."""

    class Meta:
        model = CablePath


class InterfaceType(gql_optimizer.OptimizedDjangoObjectType, PathEndpointMixin):
    """Graphql Type Object for Interface model."""

    class Meta:
        model = Interface
        filterset_class = InterfaceFilterSet
        exclude = ["_name"]

    cable_peer_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    cable_peer_front_port = graphene.Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")
    cable_peer_rear_port = graphene.Field("nautobot.dcim.graphql.types.RearPortType")
    connected_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    connected_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")
    ip_addresses = graphene.List("nautobot.ipam.graphql.types.IPAddressType")

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

    # Interface.ip_addresses is the reverse side of a GenericRelation that cannot be auto-optimized.
    # See: https://github.com/tfoxy/graphene-django-optimizer#advanced-usage
    @gql_optimizer.resolver_hints(
        model_field="ip_addresses",
    )
    def resolve_ip_addresses(self, args):
        return self.ip_addresses.all()


class ConsolePortType(gql_optimizer.OptimizedDjangoObjectType, PathEndpointMixin):
    """Graphql Type Object for ConsolePort model."""

    class Meta:
        model = ConsolePort
        filterset_class = ConsolePortFilterSet

    cable_peer_console_server_port = graphene.Field("nautobot.dcim.graphql.types.ConsoleServerPortType")
    cable_peer_front_port = graphene.Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_rear_port = graphene.Field("nautobot.dcim.graphql.types.RearPortType")
    connected_console_server_port = graphene.Field("nautobot.dcim.graphql.types.ConsoleServerPortType")

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

    def resolve_cable_peer_rear_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "RearPort":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_console_server_port(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "ConsoleServerPort":  # type built-in used to avoid class loading
            return peer
        return None


class ConsoleServerPortType(gql_optimizer.OptimizedDjangoObjectType, PathEndpointMixin):
    """Graphql Type Object for ConsoleServerPort model."""

    class Meta:
        model = ConsoleServerPort
        filterset_class = ConsoleServerPortFilterSet

    cable_peer_console_port = graphene.Field("nautobot.dcim.graphql.types.ConsolePortType")
    cable_peer_front_port = graphene.Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_rear_port = graphene.Field("nautobot.dcim.graphql.types.RearPortType")
    connected_console_port = graphene.Field("nautobot.dcim.graphql.types.ConsolePortType")

    def resolve_cable_peer_console_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "ConsolePort":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_cable_peer_front_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "FrontPort":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_cable_peer_rear_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "RearPort":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_console_port(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "ConsolePort":  # type built-in used to avoid class loading
            return peer
        return None


class FrontPortType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for FrontPort model."""

    class Meta:
        model = FrontPort
        filterset_class = FrontPortFilterSet

    cable_peer_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    cable_peer_console_port = graphene.Field("nautobot.dcim.graphql.types.ConsolePortType")
    cable_peer_console_server_port = graphene.Field("nautobot.dcim.graphql.types.ConsoleServerPortType")
    cable_peer_front_port = graphene.Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")
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

    def resolve_cable_peer_rear_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "RearPort":  # type built-in used to avoid class loading
            return peer
        return None


class PowerFeedType(gql_optimizer.OptimizedDjangoObjectType, PathEndpointMixin):
    """Graphql Type Object for PowerFeed model."""

    class Meta:
        model = PowerFeed
        filterset_class = PowerFeedFilterSet

    cable_peer_power_port = graphene.Field("nautobot.dcim.graphql.types.PowerPortType")
    connected_power_port = graphene.Field("nautobot.dcim.graphql.types.PowerPortType")

    def resolve_cable_peer_power_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "PowerPort":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_power_port(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "PowerPort":  # type built-in used to avoid class loading
            return peer
        return None


class PowerOutletType(gql_optimizer.OptimizedDjangoObjectType, PathEndpointMixin):
    """Graphql Type Object for PowerOutlet model."""

    class Meta:
        model = PowerOutlet
        filterset_class = PowerOutletFilterSet

    cable_peer_power_port = graphene.Field("nautobot.dcim.graphql.types.PowerPortType")
    connected_power_port = graphene.Field("nautobot.dcim.graphql.types.PowerPortType")

    def resolve_cable_peer_power_port(self, args):
        peer = self.get_cable_peer()
        if type(peer).__name__ == "PowerPort":  # type built-in used to avoid class loading
            return peer
        return None

    def resolve_connected_power_port(self, args):
        peer = self.connected_endpoint
        if peer and type(peer).__name__ == "PowerPort":  # type built-in used to avoid class loading
            return peer
        return None


class PowerPortType(gql_optimizer.OptimizedDjangoObjectType, PathEndpointMixin):
    """Graphql Type Object for PowerPort model."""

    class Meta:
        model = PowerPort
        filterset_class = PowerPortFilterSet

    cable_peer_power_feed = graphene.Field("nautobot.dcim.graphql.types.PowerFeedType")
    cable_peer_power_outlet = graphene.Field("nautobot.dcim.graphql.types.PowerOutletType")
    connected_power_feed = graphene.Field("nautobot.dcim.graphql.types.PowerFeedType")
    connected_power_outlet = graphene.Field("nautobot.dcim.graphql.types.PowerOutletType")

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


class RearPortType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for RearPort model."""

    class Meta:
        model = RearPort
        filterset_class = RearPortFilterSet

    cable_peer_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    cable_peer_console_port = graphene.Field("nautobot.dcim.graphql.types.ConsolePortType")
    cable_peer_console_server_port = graphene.Field("nautobot.dcim.graphql.types.ConsoleServerPortType")
    cable_peer_front_port = graphene.Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")

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


class CableTerminationTypes(graphene.Union):
    """GraphQL type for models that can be terminated on a cable."""

    class Meta:
        types = (
            ConsolePortType,
            ConsoleServerPortType,
            CircuitTerminationType,
            FrontPortType,
            InterfaceType,
            PowerFeedType,
            PowerOutletType,
            PowerPortType,
            RearPortType,
        )

    @classmethod
    def resolve_type(cls, instance, info):
        if type(instance).__name__ == "ConsolePort":
            return ConsolePortType

        if type(instance).__name__ == "ConsoleServerPort":
            return ConsoleServerPortType

        if type(instance).__name__ == "CircuitTermination":
            return CircuitTerminationType

        if type(instance).__name__ == "FrontPort":
            return FrontPortType

        if type(instance).__name__ == "Interface":
            return InterfaceType

        if type(instance).__name__ == "PowerFeed":
            return PowerFeedType

        if type(instance).__name__ == "PowerOutlet":
            return PowerOutletType

        if type(instance).__name__ == "PowerPort":
            return PowerPortType

        if type(instance).__name__ == "RearPort":
            return RearPortType

        return None
