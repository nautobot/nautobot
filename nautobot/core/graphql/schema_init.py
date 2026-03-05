import graphene
from opentelemetry import trace

from .schema import generate_query_mixin

_tracer = trace.get_tracer("nautobot.graphql")

with _tracer.start_as_current_span("graphql.schema.generate"):
    DynamicGraphQL = generate_query_mixin()


class Query(graphene.ObjectType, DynamicGraphQL):
    """Contains the entire GraphQL Schema definition for Nautobot."""


with _tracer.start_as_current_span("graphql.schema.build"):
    schema = graphene.Schema(query=Query, auto_camelcase=False)
