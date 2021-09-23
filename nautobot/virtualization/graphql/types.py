import graphene

from nautobot.core.graphql.base import NautobotObjectType
from nautobot.virtualization.models import VirtualMachine, VMInterface
from nautobot.virtualization.filters import VirtualMachineFilterSet, VMInterfaceFilterSet


class VirtualMachineType(NautobotObjectType):
    """GraphQL type object for VirtualMachine model."""

    class Meta:
        model = VirtualMachine
        filterset_class = VirtualMachineFilterSet


class VMInterfaceType(NautobotObjectType):
    """GraphQL type object for VMInterface model."""

    class Meta:
        model = VMInterface
        filterset_class = VMInterfaceFilterSet
        exclude = ["_name"]

    ip_addresses = graphene.List("nautobot.ipam.graphql.types.IPAddressType")

    def resolve_ip_addresses(self, args):
        return self.ip_addresses.all()
