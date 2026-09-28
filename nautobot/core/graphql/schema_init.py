import graphene

from nautobot.core.utils.otel import traced_span

from .schema import generate_query_mixin

with traced_span("nautobot.graphql", "graphql.schema.generate"):
    DynamicGraphQL = generate_query_mixin()


class Query(graphene.ObjectType, DynamicGraphQL):
    """Contains the entire GraphQL Schema definition for Nautobot."""


with traced_span("nautobot.graphql", "graphql.schema.build"):
    schema = graphene.Schema(query=Query, auto_camelcase=False)
