import graphene
from graphene_django import DjangoObjectType
from graphene_django.converter import convert_django_field

from nautobot.circuits.graphql.types import CircuitTerminationType
from nautobot.dcim.fields import MACAddressField
from nautobot.dcim.graphql.mixins import PathEndpointMixin
from nautobot.dcim.models import Cable, CablePath, ConsoleServerPort, Device, Interface, Rack, Site
from nautobot.dcim.filters import (
    CableFilterSet,
    ConsoleServerPortFilterSet,
    DeviceFilterSet,
    InterfaceFilterSet,
    RackFilterSet,
    SiteFilterSet,
)
from nautobot.extras.graphql.types import TagType  # noqa: F401


@convert_django_field.register(MACAddressField)
def convert_field_to_string(field, registry=None):
    """Convert MACAddressField to String."""
    return graphene.String()


class SiteType(DjangoObjectType):
    """Graphql Type Object for Site model."""

    class Meta:
        model = Site
        filterset_class = SiteFilterSet
        exclude = ["images", "_name"]


class DeviceType(DjangoObjectType):
    """Graphql Type Object for Device model."""

    class Meta:
        model = Device
        filterset_class = DeviceFilterSet
        exclude = ["_name"]


class RackType(DjangoObjectType):
    """Graphql Type Object for Rack model."""

    class Meta:
        model = Rack
        filterset_class = RackFilterSet
        exclude = ["images"]


class InterfaceType(DjangoObjectType, PathEndpointMixin):
    """Graphql Type Object for Interface model."""

    class Meta:
        model = Interface
        filterset_class = InterfaceFilterSet
        exclude = ["_name"]

    ip_addresses = graphene.List("nautobot.ipam.graphql.types.IPAddressType")

    def resolve_ip_addresses(self, args):
        return self.ip_addresses.all()


class ConsoleServerPortType(DjangoObjectType, PathEndpointMixin):
    """Graphql Type Object for ConsoleServerPort model."""

    class Meta:
        model = ConsoleServerPort
        filterset_class = ConsoleServerPortFilterSet


class CableType(DjangoObjectType):
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


class CablePathType(DjangoObjectType):
    """GraphQL type object for CablePath model."""

    class Meta:
        model = CablePath


class CableTerminationTypes(graphene.Union):
    """GraphQL type for models that can terminate a Circuit."""

    class Meta:
        types = (
            InterfaceType,
            ConsoleServerPortType,
            CircuitTerminationType,
        )

    @classmethod
    def resolve_type(cls, instance, info):
        if type(instance).__name__ == "Interface":
            return InterfaceType
        elif type(instance).__name__ == "CircuitTermination":
            return CircuitTerminationType
        elif type(instance).__name__ == "ConsoleServerPort":
            return ConsoleServerPortType
        return None
