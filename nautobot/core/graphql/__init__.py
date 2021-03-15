import graphene
import uuid

from django.contrib.auth.models import User
from django.db.models import JSONField
from django.db.models.fields import BinaryField
from django.test.client import RequestFactory

from nautobot.extras.models import GraphQLQuery

from graphene.types import generic
from graphene_django.converter import convert_django_field
from graphene_django.settings import graphene_settings
from graphql import get_default_backend, GraphQLError


@convert_django_field.register(JSONField)
def convert_field_to_string(field, registry=None):
    """Convert JSONField to GenericScalar."""
    return generic.GenericScalar()


@convert_django_field.register(BinaryField)  # noqa: F811
def convert_field_to_string(field, registry=None):  # noqa: F811
    """Convert BinaryField to String."""
    return graphene.String()


def execute_query(query, variables=None, request=None, user=None):
    if not request and not user:
        raise Exception("either request or username should be provided")
    if not request:
        request = RequestFactory().request(SERVER_NAME="WebRequestContext")
        request.id = uuid.uuid4()
        request.user = user
    backend = get_default_backend()
    schema = graphene_settings.SCHEMA
    document = backend.document_from_string(schema, query)
    if variables:
        return document.execute(context_value=request, variable_values=variables)
    else:
        return document.execute(context_value=request)


def execute_saved_query(saved_query, variables=None, request=None, user=None):
    query = GraphQLQuery.objects.get(slug=saved_query)
    return execute_query(query=query.query, variables=variables, request=request, user=user)
