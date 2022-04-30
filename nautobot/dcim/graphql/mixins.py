import graphene


class PathEndpointMixin:
    """Mixin for GraphQL objects that act as PathEndpoints."""

    connected_endpoint = graphene.Field("nautobot.dcim.graphql.types.PathEndpointTypes")
    path = graphene.Field("nautobot.dcim.graphql.types.CablePathType")


class CableTerminationMixin:
    """Mixin for GraphQL objects that act as CableEndpoints"""

    cable_peer = graphene.Field("nautobot.dcim.graphql.types.CableTerminationTypes")
