import graphene

from nautobot.core.graphql.types import OptimizedNautobotObjectType
from nautobot.extras.models import DynamicGroup
from nautobot.ipam import filters, models


class IPAddressType(OptimizedNautobotObjectType):
    """Graphql Type Object for IPAddress model."""

    address = graphene.String()
    ip_version = graphene.Int()
    dynamic_groups = graphene.List("nautobot.extras.graphql.types.DynamicGroupType")

    class Meta:
        model = models.IPAddress
        filterset_class = filters.IPAddressFilterSet

    def resolve_dynamic_groups(self, args):
        return DynamicGroup.objects.get_for_object(self)


class PrefixType(OptimizedNautobotObjectType):
    """Graphql Type Object for Prefix model."""

    prefix = graphene.String()
    ip_version = graphene.Int()
    dynamic_groups = graphene.List("nautobot.extras.graphql.types.DynamicGroupType")
    location = graphene.Field("nautobot.dcim.graphql.types.LocationType")

    class Meta:
        model = models.Prefix
        filterset_class = filters.PrefixFilterSet

    def resolve_dynamic_groups(self, args):
        return DynamicGroup.objects.get_for_object(self)


class VLANType(OptimizedNautobotObjectType):
    """Graphql Type Object for VLAN model."""

    location = graphene.Field("nautobot.dcim.graphql.types.LocationType")

    class Meta:
        model = models.VLAN
        filterset_class = filters.VLANFilterSet
