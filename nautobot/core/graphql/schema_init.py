import graphene
from graphene_django.types import ObjectType
from django.db.models import signals

from .schema import generate_query_mixin
from nautobot.extras.models import CustomField, Relationship

schema = None


# manipulating the global is less than pretty, but since we have to manipulate
# the state of the app from signals that might just be what we have to do
def generate_schema(*args, **kwargs):
    global schema
    DynamicGraphQL = generate_query_mixin()

    class Query(ObjectType, DynamicGraphQL):
        """Contains the entire GraphQL Schema definition for Nautobot."""

    schema = graphene.Schema(query=Query, auto_camelcase=False)


# generate the initial schema
generate_schema()


signals.post_save.connect(generate_schema, sender=Relationship)
signals.post_delete.connect(generate_schema, sender=Relationship)
signals.post_save.connect(generate_schema, sender=CustomField)
signals.post_delete.connect(generate_schema, sender=CustomField)
