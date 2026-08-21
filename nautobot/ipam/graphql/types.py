import graphene

from nautobot.core.graphql.types import OptimizedNautobotObjectType
from nautobot.core.graphql.utils import permission_safe_attribute_resolver
from nautobot.ipam import filters, models


class IPAddressType(OptimizedNautobotObjectType):
    """Graphql Type Object for IPAddress model."""

    address = graphene.String()
    ip_version = graphene.Int()

    class Meta:
        model = models.IPAddress
        filterset_class = filters.IPAddressFilterSet


class IPAddressRangeType(OptimizedNautobotObjectType):
    """Graphql Type Object for IPAddressRange model."""

    start_address = graphene.String()
    end_address = graphene.String()
    ip_version = graphene.Int()

    class Meta:
        model = models.IPAddressRange
        filterset_class = filters.IPAddressRangeFilterSet


class PrefixType(OptimizedNautobotObjectType):
    """Graphql Type Object for Prefix model."""

    prefix = graphene.String()
    ip_version = graphene.Int()
    location = graphene.Field("nautobot.dcim.graphql.types.LocationType")

    class Meta:
        model = models.Prefix
        filterset_class = filters.PrefixFilterSet

    # `location` is a legacy model property (Prefix uses the `locations` M2M), so it bypasses the
    # auto-generated permission-enforcing resolvers; wrap it to hide a location the user may not view.
    resolve_location = permission_safe_attribute_resolver("location")


class VLANType(OptimizedNautobotObjectType):
    """Graphql Type Object for VLAN model."""

    location = graphene.Field("nautobot.dcim.graphql.types.LocationType")

    class Meta:
        model = models.VLAN
        filterset_class = filters.VLANFilterSet

    # `location` is a legacy model property (VLAN uses the `locations` M2M), so it bypasses the
    # auto-generated permission-enforcing resolvers; wrap it to hide a location the user may not view.
    resolve_location = permission_safe_attribute_resolver("location")
