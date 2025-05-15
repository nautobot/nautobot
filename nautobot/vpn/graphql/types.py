"""GraphQL implementation for the vpn models."""

import graphene
from graphene_django import DjangoObjectType

from nautobot.vpn.models import VPNTunnelEndpoint
from nautobot.vpn.filters import VPNTunnelEndpointFilterSet


class VPNTunnelEndpointType(DjangoObjectType):
    """Graphql Type Object for the VPNTunnelEndpoint model."""

    name = graphene.String()

    class Meta:
        """Metadata for the VPNTunnelEndpoint."""

        model = VPNTunnelEndpoint
        filterset_class = VPNTunnelEndpointFilterSet


graphql_types = [
    VPNTunnelEndpointType,
]
