import graphene
import graphene_django_optimizer as gql_optimizer

from nautobot.extras.models import DynamicGroup
from nautobot.ipam import models, filters


class IPAddressType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for IPAddress model."""

    address = graphene.String()
    interface = graphene.Field("nautobot.dcim.graphql.types.InterfaceType")
    vminterface = graphene.Field("nautobot.virtualization.graphql.types.VMInterfaceType")
    dynamic_groups = graphene.List("nautobot.extras.graphql.types.DynamicGroupType")

    class Meta:
        model = models.IPAddress
        filterset_class = filters.IPAddressFilterSet

    # TODO: update to work with interface M2M
    def resolve_interface(self, args):
        return None

    # TODO: update to work with interface M2M
    def resolve_vminterface(self, args):
        return None

    def resolve_dynamic_groups(self, args):
        return DynamicGroup.objects.get_for_objectƒ(self)


class PrefixType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for Prefix model."""

    prefix = graphene.String()
    dynamic_groups = graphene.List("nautobot.extras.graphql.types.DynamicGroupType")

    class Meta:
        model = models.Prefix
        filterset_class = filters.PrefixFilterSet

    def resolve_dynamic_groups(self, args):
        return DynamicGroup.objects.get_for_object(self)
