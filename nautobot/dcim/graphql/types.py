import graphene
import graphene_django_optimizer as gql_optimizer

from nautobot.circuits.graphql.types import CircuitTerminationType
from nautobot.dcim.graphql.mixins import CablePeerEndpointMixin, PathEndpointMixin
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


class InterfaceType(gql_optimizer.OptimizedDjangoObjectType, CablePeerEndpointMixin, PathEndpointMixin):
    """Graphql Type Object for Interface model."""

    class Meta:
        model = Interface
        filterset_class = InterfaceFilterSet
        exclude = ["_name"]

    ip_addresses = graphene.List("nautobot.ipam.graphql.types.IPAddressType")

    # Interface.ip_addresses is the reverse side of a GenericRelation that cannot be auto-optimized.
    # See: https://github.com/tfoxy/graphene-django-optimizer#advanced-usage
    @gql_optimizer.resolver_hints(
        model_field="ip_addresses",
    )
    def resolve_ip_addresses(self, args):
        return self.ip_addresses.all()


class ConsolePortType(gql_optimizer.OptimizedDjangoObjectType, CablePeerEndpointMixin, PathEndpointMixin):
    """Graphql Type Object for ConsolePort model."""

    class Meta:
        model = ConsolePort
        filterset_class = ConsolePortFilterSet


class ConsoleServerPortType(gql_optimizer.OptimizedDjangoObjectType, CablePeerEndpointMixin, PathEndpointMixin):
    """Graphql Type Object for ConsoleServerPort model."""

    class Meta:
        model = ConsoleServerPort
        filterset_class = ConsoleServerPortFilterSet


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


class FrontPortType(gql_optimizer.OptimizedDjangoObjectType, CablePeerEndpointMixin):
    """Graphql Type Object for ConsoleServerPort model."""

    class Meta:
        model = FrontPort
        filterset_class = FrontPortFilterSet


class PowerFeedType(gql_optimizer.OptimizedDjangoObjectType, CablePeerEndpointMixin, PathEndpointMixin):
    """Graphql Type Object for ConsoleServerPort model."""

    class Meta:
        model = PowerFeed
        filterset_class = PowerFeedFilterSet


class PowerOutletType(gql_optimizer.OptimizedDjangoObjectType, PathEndpointMixin):
    """Graphql Type Object for ConsoleServerPort model."""

    class Meta:
        model = PowerOutlet
        filterset_class = PowerOutletFilterSet


class PowerPortType(gql_optimizer.OptimizedDjangoObjectType, CablePeerEndpointMixin, PathEndpointMixin):
    """Graphql Type Object for ConsoleServerPort model."""

    class Meta:
        model = PowerPort
        filterset_class = PowerPortFilterSet


class RearPortType(gql_optimizer.OptimizedDjangoObjectType, CablePeerEndpointMixin):
    """Graphql Type Object for ConsoleServerPort model."""

    class Meta:
        model = RearPort
        filterset_class = RearPortFilterSet


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
        type_mapping = {
            "ConsolePort": ConsolePortType,
            "ConsoleServerPort": ConsoleServerPortType,
            "CircuitTermination": CircuitTerminationType,
            "FrontPort": FrontPortType,
            "Interface": InterfaceType,
            "PowerFeed": PowerFeedType,
            "PowerOutlet": PowerOutletType,
            "PowerPort": PowerPortType,
            "RearPort": RearPortType,
        }
        if type(instance).__name__ in type_mapping:
            return type_mapping[type(instance).__name__]

        return None
