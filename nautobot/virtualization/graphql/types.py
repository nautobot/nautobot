import graphene
from graphene_django import DjangoObjectType

from nautobot.virtualization.models import VMInterface
from nautobot.virtualization.filters import VMInterfaceFilterSet


class VMInterfaceType(DjangoObjectType):
    """GraphQL type object for VMInterface model."""

    class Meta:
        model = VMInterface
        filterset_class = VMInterfaceFilterSet
        exclude = ["_name"]

    ip_addresses = graphene.List("nautobot.ipam.graphql.types.IPAddressType")

    def resolve_ip_addresses(self, args):
        return self.ip_addresses.all()
