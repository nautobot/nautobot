import graphene


class PathEndpointMixin:
    """Mixin for GraphQL objects that act as PathEndpoints."""

    connected_endpoint = graphene.Field("nautobot.dcim.graphql.types.CableTerminationTypes")
    path = graphene.Field("nautobot.dcim.graphql.types.CablePathType")
