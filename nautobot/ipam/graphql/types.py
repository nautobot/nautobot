import graphene

from nautobot.core.graphql.types import OptimizedNautobotObjectType
from nautobot.extras.models import DynamicGroup
from nautobot.ipam import models, filters


class IPAddressType(OptimizedNautobotObjectType):
    """Graphql Type Object for IPAddress model."""

    address = graphene.String()
    ip_version = graphene.Int()
    dynamic_groups = graphene.List("nautobot.extras.graphql.types.DynamicGroupType")

    class Meta:
        model = models.IPAddress
        filterset_class = filters.IPAddressFilterSet

    def resolve_dynamic_groups(self, args):
        return DynamicGroup.objects.get_for_object(self, use_cache=True)


class PrefixType(OptimizedNautobotObjectType):
    """Graphql Type Object for Prefix model."""

    prefix = graphene.String()
    ip_version = graphene.Int()
    dynamic_groups = graphene.List("nautobot.extras.graphql.types.DynamicGroupType")

    class Meta:
        model = models.Prefix
        filterset_class = filters.PrefixFilterSet

    def resolve_dynamic_groups(self, args):
        return DynamicGroup.objects.get_for_object(self, use_cache=True)
