import graphene
from graphene_django.types import ObjectType

from .schema import generate_query_mixin


DynamicGraphQL = generate_query_mixin()


class Query(ObjectType, DynamicGraphQL):
    """Contains the entire GraphQL Schema definition for Nautobot."""


schema = graphene.Schema(query=Query, auto_camelcase=False)
