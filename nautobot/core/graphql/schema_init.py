import graphene
from graphene_django.types import ObjectType
from django.db.models import signals

from .schema import generate_query_mixin
from nautobot.extras.models import CustomField, Relationship


def generate_schema(*args, **kwargs):
    DynamicGraphQL = generate_query_mixin()

    class Query(ObjectType, DynamicGraphQL):
        """Contains the entire GraphQL Schema definition for Nautobot."""

    return graphene.Schema(query=Query, auto_camelcase=False)


schema = generate_schema()

signals.post_save.connect(generate_schema, sender=Relationship)
signals.post_delete.connect(generate_schema, sender=Relationship)
signals.post_save.connect(generate_schema, sender=CustomField)
signals.post_delete.connect(generate_schema, sender=CustomField)
