import graphene
import graphene_django_optimizer as gql_optimizer

from nautobot.core.graphql.utils import construct_resolver
from nautobot.circuits.graphql.types import CircuitTerminationType
from nautobot.dcim.graphql.mixins import CableTerminationMixin, PathEndpointMixin
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
from nautobot.extras.models import DynamicGroup


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

    dynamic_groups = graphene.List("nautobot.extras.graphql.types.DynamicGroupType")

    def resolve_dynamic_groups(self, args):
        return DynamicGroup.objects.get_for_object(self)


class RackType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for Rack model."""

    class Meta:
        model = Rack
        filterset_class = RackFilterSet
        exclude = ["images"]

    dynamic_groups = graphene.List("nautobot.extras.graphql.types.DynamicGroupType")

    def resolve_dynamic_groups(self, args):
        return DynamicGroup.objects.get_for_object(self)


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


class InterfaceType(gql_optimizer.OptimizedDjangoObjectType, CableTerminationMixin, PathEndpointMixin):
    """Graphql Type Object for Interface model."""

    class Meta:
        model = Interface
        filterset_class = InterfaceFilterSet
        exclude = ["_name"]

    # Field Definitions
    cable_peer_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    cable_peer_front_port = graphene.Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")
    cable_peer_rear_port = graphene.Field("nautobot.dcim.graphql.types.RearPortType")
    connected_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    connected_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")
    ip_addresses = graphene.List("nautobot.ipam.graphql.types.IPAddressType")

    # Resolver Definitions
    resolve_cable_peer_circuit_termination = construct_resolver("CircuitTermination", "cable_peer")
    resolve_cable_peer_front_port = construct_resolver("FrontPort", "cable_peer")
    resolve_cable_peer_interface = construct_resolver("Interface", "cable_peer")
    resolve_cable_peer_rear_port = construct_resolver("RearPort", "cable_peer")
    resolve_connected_circuit_termination = construct_resolver("CircuitTermination", "connected_endpoint")
    resolve_connected_interface = construct_resolver("Interface", "connected_endpoint")

    # Interface.ip_addresses is the reverse side of a GenericRelation that cannot be auto-optimized.
    # See: https://github.com/tfoxy/graphene-django-optimizer#advanced-usage
    @gql_optimizer.resolver_hints(
        model_field="ip_addresses",
    )
    def resolve_ip_addresses(self, args):
        return self.ip_addresses.all()


class ConsolePortType(gql_optimizer.OptimizedDjangoObjectType, CableTerminationMixin, PathEndpointMixin):
    """Graphql Type Object for ConsolePort model."""

    class Meta:
        model = ConsolePort
        filterset_class = ConsolePortFilterSet

    # Field Definitions
    cable_peer_console_server_port = graphene.Field("nautobot.dcim.graphql.types.ConsoleServerPortType")
    cable_peer_front_port = graphene.Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_rear_port = graphene.Field("nautobot.dcim.graphql.types.RearPortType")
    connected_console_server_port = graphene.Field("nautobot.dcim.graphql.types.ConsoleServerPortType")

    # Resolver Definitions
    resolve_cable_peer_console_server_port = construct_resolver("ConsoleServerPort", "cable_peer")
    resolve_cable_peer_front_port = construct_resolver("FrontPort", "cable_peer")
    resolve_cable_peer_rear_port = construct_resolver("RearPort", "cable_peer")
    resolve_connected_console_server_port = construct_resolver("ConsoleServerPort", "connected_endpoint")


class ConsoleServerPortType(gql_optimizer.OptimizedDjangoObjectType, CableTerminationMixin, PathEndpointMixin):
    """Graphql Type Object for ConsoleServerPort model."""

    class Meta:
        model = ConsoleServerPort
        filterset_class = ConsoleServerPortFilterSet

    # Field Definitions
    cable_peer_console_port = graphene.Field("nautobot.dcim.graphql.types.ConsolePortType")
    cable_peer_front_port = graphene.Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_rear_port = graphene.Field("nautobot.dcim.graphql.types.RearPortType")
    connected_console_port = graphene.Field("nautobot.dcim.graphql.types.ConsolePortType")

    # Resolver Definitions
    resolve_cable_peer_console_port = construct_resolver("ConsolePort", "cable_peer")
    resolve_cable_peer_front_port = construct_resolver("FrontPort", "cable_peer")
    resolve_cable_peer_rear_port = construct_resolver("RearPort", "cable_peer")
    resolve_connected_console_port = construct_resolver("ConsolePort", "connected_endpoint")


class FrontPortType(gql_optimizer.OptimizedDjangoObjectType, CableTerminationMixin):
    """Graphql Type Object for FrontPort model."""

    class Meta:
        model = FrontPort
        filterset_class = FrontPortFilterSet

    # Field Definitions
    cable_peer_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    cable_peer_console_port = graphene.Field("nautobot.dcim.graphql.types.ConsolePortType")
    cable_peer_console_server_port = graphene.Field("nautobot.dcim.graphql.types.ConsoleServerPortType")
    cable_peer_front_port = graphene.Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")
    cable_peer_rear_port = graphene.Field("nautobot.dcim.graphql.types.RearPortType")

    # Resolver Definitions
    resolve_cable_peer_circuit_termination = construct_resolver("CircuitTermination", "cable_peer")
    resolve_cable_peer_console_port = construct_resolver("ConsolePort", "cable_peer")
    resolve_cable_peer_console_server_port = construct_resolver("ConsoleServerPort", "cable_peer")
    resolve_cable_peer_front_port = construct_resolver("FrontPort", "cable_peer")
    resolve_cable_peer_interface = construct_resolver("Interface", "cable_peer")
    resolve_cable_peer_rear_port = construct_resolver("RearPort", "cable_peer")


class PowerFeedType(gql_optimizer.OptimizedDjangoObjectType, CableTerminationMixin, PathEndpointMixin):
    """Graphql Type Object for PowerFeed model."""

    class Meta:
        model = PowerFeed
        filterset_class = PowerFeedFilterSet

    # Field Definitions
    cable_peer_power_port = graphene.Field("nautobot.dcim.graphql.types.PowerPortType")
    connected_power_port = graphene.Field("nautobot.dcim.graphql.types.PowerPortType")

    # Resolver Definitions
    resolve_cable_peer_power_port = construct_resolver("PowerPort", "cable_peer")
    resolve_connected_power_port = construct_resolver("PowerPort", "connected_endpoint")


class PowerOutletType(gql_optimizer.OptimizedDjangoObjectType, CableTerminationMixin, PathEndpointMixin):
    """Graphql Type Object for PowerOutlet model."""

    class Meta:
        model = PowerOutlet
        filterset_class = PowerOutletFilterSet

    # Field Definitions
    cable_peer_power_port = graphene.Field("nautobot.dcim.graphql.types.PowerPortType")
    connected_power_port = graphene.Field("nautobot.dcim.graphql.types.PowerPortType")

    # Resolver Definitions
    resolve_cable_peer_power_port = construct_resolver("PowerPort", "cable_peer")
    resolve_connected_power_port = construct_resolver("PowerPort", "connected_endpoint")


class PowerPortType(gql_optimizer.OptimizedDjangoObjectType, CableTerminationMixin, PathEndpointMixin):
    """Graphql Type Object for PowerPort model."""

    class Meta:
        model = PowerPort
        filterset_class = PowerPortFilterSet

    # Field Definitions
    cable_peer_power_feed = graphene.Field("nautobot.dcim.graphql.types.PowerFeedType")
    cable_peer_power_outlet = graphene.Field("nautobot.dcim.graphql.types.PowerOutletType")
    connected_power_feed = graphene.Field("nautobot.dcim.graphql.types.PowerFeedType")
    connected_power_outlet = graphene.Field("nautobot.dcim.graphql.types.PowerOutletType")

    # Resolver Definitions
    resolve_cable_peer_power_feed = construct_resolver("PowerFeed", "cable_peer")
    resolve_cable_peer_power_outlet = construct_resolver("PowerOutlet", "cable_peer")
    resolve_connected_power_feed = construct_resolver("PowerFeed", "connected_endpoint")
    resolve_connected_power_outlet = construct_resolver("PowerOutlet", "connected_endpoint")


class RearPortType(gql_optimizer.OptimizedDjangoObjectType, CableTerminationMixin):
    """Graphql Type Object for RearPort model."""

    class Meta:
        model = RearPort
        filterset_class = RearPortFilterSet

    # Field Definitions
    cable_peer_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    cable_peer_console_port = graphene.Field("nautobot.dcim.graphql.types.ConsolePortType")
    cable_peer_console_server_port = graphene.Field("nautobot.dcim.graphql.types.ConsoleServerPortType")
    cable_peer_front_port = graphene.Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_rear_port = graphene.Field("nautobot.dcim.graphql.types.RearPortType")
    cable_peer_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")

    # Resolver Definitions
    resolve_cable_peer_circuit_termination = construct_resolver("CircuitTermination", "cable_peer")
    resolve_cable_peer_console_port = construct_resolver("ConsolePort", "cable_peer")
    resolve_cable_peer_console_server_port = construct_resolver("ConsoleServerPort", "cable_peer")
    resolve_cable_peer_front_port = construct_resolver("FrontPort", "cable_peer")
    resolve_cable_peer_interface = construct_resolver("Interface", "cable_peer")
    resolve_cable_peer_rear_port = construct_resolver("RearPort", "cable_peer")


class PathEndpointTypes(graphene.Union):
    """GraphQL type for models that can be terminated on a PathEndpoint."""

    class Meta:
        types = (
            ConsolePortType,
            ConsoleServerPortType,
            CircuitTerminationType,
            InterfaceType,
            PowerFeedType,
            PowerOutletType,
            PowerPortType,
        )

    @classmethod
    def resolve_type(cls, instance, info):
        if type(instance).__name__ == "ConsolePort":
            return ConsolePortType

        if type(instance).__name__ == "ConsoleServerPort":
            return ConsoleServerPortType

        if type(instance).__name__ == "CircuitTermination":
            return CircuitTerminationType

        if type(instance).__name__ == "Interface":
            return InterfaceType

        if type(instance).__name__ == "PowerFeed":
            return PowerFeedType

        if type(instance).__name__ == "PowerOutlet":
            return PowerOutletType

        if type(instance).__name__ == "PowerPort":
            return PowerPortType

        return None


class CableTerminationTypes(graphene.Union):
    """GraphQL type for models that can be terminated on a Cable."""

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
