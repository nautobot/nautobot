import graphene

from nautobot.core.graphql.utils import permission_safe_attribute_resolver


class PathEndpointMixin:
    """Mixin for GraphQL objects that act as PathEndpoints."""

    connected_endpoint = graphene.Field("nautobot.dcim.graphql.types.PathEndpointTypes")
    path = graphene.Field("nautobot.dcim.graphql.types.CablePathType")

    # `connected_endpoint` and `path` are model properties, so they bypass the auto-generated
    # permission-enforcing resolvers; wrap them so a peer/path the user may not view is returned as null.
    resolve_connected_endpoint = permission_safe_attribute_resolver("connected_endpoint")
    resolve_path = permission_safe_attribute_resolver("path")


class CableTerminationMixin:
    """Mixin for GraphQL objects that act as CableEndpoints"""

    cable = graphene.Field("nautobot.dcim.graphql.types.CableType")
    cable_peer = graphene.Field("nautobot.dcim.graphql.types.CableTerminationTypes")

    resolve_cable = permission_safe_attribute_resolver("cable")
    resolve_cable_peer = permission_safe_attribute_resolver("cable_peer")
