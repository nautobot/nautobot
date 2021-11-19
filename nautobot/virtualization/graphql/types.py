import graphene
import graphene_django_optimizer as gql_optimizer

from nautobot.virtualization.models import VirtualMachine, VMInterface
from nautobot.virtualization.filters import VirtualMachineFilterSet, VMInterfaceFilterSet


class VirtualMachineType(gql_optimizer.OptimizedDjangoObjectType):
    """GraphQL type object for VirtualMachine model."""

    class Meta:
        model = VirtualMachine
        filterset_class = VirtualMachineFilterSet


class VMInterfaceType(gql_optimizer.OptimizedDjangoObjectType):
    """GraphQL type object for VMInterface model."""

    class Meta:
        model = VMInterface
        filterset_class = VMInterfaceFilterSet
        exclude = ["_name"]

    ip_addresses = graphene.List("nautobot.ipam.graphql.types.IPAddressType")

    # VMInterface.ip_addresses is the reverse side of a GenericRelation that cannot be auto-optimized.
    # See: https://github.com/tfoxy/graphene-django-optimizer#advanced-usage
    @gql_optimizer.resolver_hints(
        model_field="ip_addresses",
    )
    def resolve_ip_addresses(self, args):
        return self.ip_addresses.all()
