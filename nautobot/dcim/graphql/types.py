import graphene

from nautobot.circuits.graphql.types import CircuitTerminationType
from nautobot.core.graphql.types import OptimizedNautobotObjectType
from nautobot.core.graphql.utils import construct_resolver
from nautobot.dcim.filters import (
    CableFilterSet,
    ConsolePortFilterSet,
    ConsoleServerPortFilterSet,
    DeviceFilterSet,
    FrontPortFilterSet,
    InterfaceFilterSet,
    LocationFilterSet,
    ModuleBayFilterSet,
    ModuleFilterSet,
    PlatformFilterSet,
    PowerFeedFilterSet,
    PowerOutletFilterSet,
    PowerPortFilterSet,
    RackFilterSet,
    RearPortFilterSet,
)
from nautobot.dcim.graphql.mixins import CableTerminationMixin, PathEndpointMixin
from nautobot.dcim.models import (
    Cable,
    CablePath,
    ConsolePort,
    ConsoleServerPort,
    Device,
    FrontPort,
    Interface,
    Location,
    Module,
    ModuleBay,
    Platform,
    PowerFeed,
    PowerOutlet,
    PowerPort,
    Rack,
    RearPort,
)
from nautobot.extras.models import DynamicGroup


class LocationType(OptimizedNautobotObjectType):
    """Graphql Type Object for Location model."""

    class Meta:
        model = Location
        filterset_class = LocationFilterSet
        exclude = ["images", "_name"]


class DeviceType(OptimizedNautobotObjectType):
    """Graphql Type Object for Device model."""

    class Meta:
        model = Device
        filterset_class = DeviceFilterSet
        exclude = ["_name"]

    all_console_ports = graphene.List("nautobot.dcim.graphql.types.ConsolePortType")
    all_console_server_ports = graphene.List("nautobot.dcim.graphql.types.ConsoleServerPortType")
    all_front_ports = graphene.List("nautobot.dcim.graphql.types.FrontPortType")
    all_interfaces = graphene.List("nautobot.dcim.graphql.types.InterfaceType")
    all_module_bays = graphene.List("nautobot.dcim.graphql.types.ModuleBayType")
    all_modules = graphene.List("nautobot.dcim.graphql.types.ModuleType")
    all_power_ports = graphene.List("nautobot.dcim.graphql.types.PowerPortType")
    all_power_outlets = graphene.List("nautobot.dcim.graphql.types.PowerOutletType")
    all_rear_ports = graphene.List("nautobot.dcim.graphql.types.RearPortType")
    common_vc_interfaces = graphene.List("nautobot.dcim.graphql.types.InterfaceType")
    dynamic_groups = graphene.List("nautobot.extras.graphql.types.DynamicGroupType")
    primary_ip = graphene.Field("nautobot.ipam.graphql.types.IPAddressType")
    vc_interfaces = graphene.List("nautobot.dcim.graphql.types.InterfaceType")

    def resolve_dynamic_groups(self, args):
        return DynamicGroup.objects.get_for_object(self)


class ModuleBayType(OptimizedNautobotObjectType):
    class Meta:
        model = ModuleBay
        filterset_class = ModuleBayFilterSet


class ModuleType(OptimizedNautobotObjectType):
    device = graphene.Field("nautobot.dcim.graphql.types.DeviceType")

    class Meta:
        model = Module
        filterset_class = ModuleFilterSet


class PlatformType(OptimizedNautobotObjectType):
    """GraphQL type object for Platform model."""

    network_driver_mappings = graphene.types.generic.GenericScalar()

    class Meta:
        model = Platform
        filterset_class = PlatformFilterSet


class RackType(OptimizedNautobotObjectType):
    """Graphql Type Object for Rack model."""

    class Meta:
        model = Rack
        filterset_class = RackFilterSet
        exclude = ["images"]

    dynamic_groups = graphene.List("nautobot.extras.graphql.types.DynamicGroupType")

    def resolve_dynamic_groups(self, args):
        return DynamicGroup.objects.get_for_object(self)


class CableType(OptimizedNautobotObjectType):
    """Graphql Type Object for Cable model."""

    class Meta:
        model = Cable
        filterset_class = CableFilterSet
        exclude = ["_termination_a_device", "_termination_b_device"]

    termination_a_type = graphene.String()
    termination_b_type = graphene.String()

    def resolve_termination_a_type(self, args):
        if self.termination_a_type:
            model = self.termination_a_type.model_class()  # pylint: disable=no-member
            return f"{model._meta.app_label}.{model._meta.model_name}"
        return None

    def resolve_termination_b_type(self, args):
        if self.termination_b_type:
            model = self.termination_b_type.model_class()  # pylint: disable=no-member
            return f"{model._meta.app_label}.{model._meta.model_name}"
        return None


class CablePathType(OptimizedNautobotObjectType):
    """GraphQL type object for CablePath model."""

    class Meta:
        model = CablePath


class InterfaceType(OptimizedNautobotObjectType, CableTerminationMixin, PathEndpointMixin):
    """Graphql Type Object for Interface model."""

    class Meta:
        model = Interface
        filterset_class = InterfaceFilterSet
        exclude = ["_name"]

    # At the DB level, mac_address is null=False, but empty strings are represented as null in the ORM and REST API,
    # so for consistency, we'll keep that same representation in GraphQL.
    mac_address = graphene.String(required=False)

    # Field Definitions
    cable_peer_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    cable_peer_front_port = graphene.Field("nautobot.dcim.graphql.types.FrontPortType")
    cable_peer_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")
    cable_peer_rear_port = graphene.Field("nautobot.dcim.graphql.types.RearPortType")
    connected_circuit_termination = graphene.Field("nautobot.circuits.graphql.types.CircuitTerminationType")
    connected_interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")

    # Resolver Definitions
    resolve_cable_peer_circuit_termination = construct_resolver("CircuitTermination", "cable_peer")
    resolve_cable_peer_front_port = construct_resolver("FrontPort", "cable_peer")
    resolve_cable_peer_interface = construct_resolver("Interface", "cable_peer")
    resolve_cable_peer_rear_port = construct_resolver("RearPort", "cable_peer")
    resolve_connected_circuit_termination = construct_resolver("CircuitTermination", "connected_endpoint")
    resolve_connected_interface = construct_resolver("Interface", "connected_endpoint")


class ConsolePortType(OptimizedNautobotObjectType, CableTerminationMixin, PathEndpointMixin):
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


class ConsoleServerPortType(OptimizedNautobotObjectType, CableTerminationMixin, PathEndpointMixin):
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


class FrontPortType(OptimizedNautobotObjectType, CableTerminationMixin):
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


class PowerFeedType(OptimizedNautobotObjectType, CableTerminationMixin, PathEndpointMixin):
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


class PowerOutletType(OptimizedNautobotObjectType, CableTerminationMixin, PathEndpointMixin):
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


class PowerPortType(OptimizedNautobotObjectType, CableTerminationMixin, PathEndpointMixin):
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


class RearPortType(OptimizedNautobotObjectType, CableTerminationMixin):
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
