import graphene
from graphene_django.types import ObjectType

from .schema import generate_query_mixin


def generate_schema():
    DynamicGraphQL = generate_query_mixin()

    class Query(ObjectType, DynamicGraphQL):
        """Contains the entire GraphQL Schema definition for Nautobot."""

    return graphene.Schema(query=Query, auto_camelcase=False)
