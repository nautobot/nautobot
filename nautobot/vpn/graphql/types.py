"""GraphQL implementation for the vpn models."""

import graphene

from nautobot.core.graphql.types import OptimizedNautobotObjectType
from nautobot.vpn.filters import VPNTunnelEndpointFilterSet
from nautobot.vpn.models import VPNTunnelEndpoint


class VPNTunnelEndpointType(OptimizedNautobotObjectType):
    """Graphql Type Object for the VPNTunnelEndpoint model."""

    name = graphene.String()

    class Meta:
        """Metadata for the VPNTunnelEndpoint."""

        model = VPNTunnelEndpoint
        filterset_class = VPNTunnelEndpointFilterSet


graphql_types = [
    VPNTunnelEndpointType,
]
