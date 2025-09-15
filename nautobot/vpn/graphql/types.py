"""GraphQL implementation for the vpn models."""

import graphene

from nautobot.core.graphql.types import OptimizedNautobotObjectType
from nautobot.vpn.filters import VPNProfileFilterSet, VPNTunnelEndpointFilterSet, VPNTunnelFilterSet
from nautobot.vpn.models import VPNProfile, VPNTunnel, VPNTunnelEndpoint


class VPNProfileType(OptimizedNautobotObjectType):
    """GraphQL type for VPNProfile."""

    class Meta:
        model = VPNProfile
        filterset_class = VPNProfileFilterSet


class VPNTunnelType(OptimizedNautobotObjectType):
    """GraphQL type for VPNTunnel."""

    vpn_profile = graphene.Field(VPNProfileType)

    class Meta:
        model = VPNTunnel
        filterset_class = VPNTunnelFilterSet


class VPNTunnelEndpointType(OptimizedNautobotObjectType):
    """Graphql Type Object for the VPNTunnelEndpoint model."""

    name = graphene.String()

    class Meta:
        """Metadata for the VPNTunnelEndpoint."""

        model = VPNTunnelEndpoint
        filterset_class = VPNTunnelEndpointFilterSet


graphql_types = [
    VPNTunnelType,
    VPNTunnelEndpointType,
]
