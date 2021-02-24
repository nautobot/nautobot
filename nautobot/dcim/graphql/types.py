import graphene
from graphene_django import DjangoObjectType
from graphene_django.converter import convert_django_field

from nautobot.dcim.fields import MACAddressField
from nautobot.dcim.models import Site, Device, Interface, Rack, Cable, ConsoleServerPort
from nautobot.dcim.filters import (
    SiteFilterSet,
    DeviceFilterSet,
    InterfaceFilterSet,
    RackFilterSet,
    CableFilterSet,
    ConsoleServerPortFilterSet,
)
from nautobot.ipam.graphql.types import IPAddressType
from nautobot.extras.graphql.types import TagType  # noqa: F401


@convert_django_field.register(MACAddressField)
def convert_field_to_string(field, registry=None):
    """Convert MACAddressField to String."""
    return graphene.String()


class CableTerminationMixin:
    """Mixin for CableTermination for GraphQL objects."""

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


class InterfaceType(DjangoObjectType, CableTerminationMixin):
    """Graphql Type Object for Interface model."""

    class Meta:
        model = Interface
        filterset_class = InterfaceFilterSet
        exclude = ["_name"]

    ip_addresses = graphene.List(IPAddressType)

    def resolve_ip_addresses(self, args):
        return self.ip_addresses.all()


class ConsoleServerPortType(DjangoObjectType, CableTerminationMixin):
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
