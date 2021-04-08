import graphene

from django.db.models import JSONField
from django.db.models.fields import BinaryField
from django.test.client import RequestFactory

from nautobot.extras.context_managers import web_request_context
from nautobot.extras.models import GraphQLQuery

from graphene.types import generic
from graphene_django.converter import convert_django_field
from graphene_django.settings import graphene_settings
from graphql import get_default_backend


@convert_django_field.register(JSONField)
def convert_field_to_string(field, registry=None):
    """Convert JSONField to GenericScalar."""
    return generic.GenericScalar()


@convert_django_field.register(BinaryField)  # noqa: F811
def convert_field_to_string(field, registry=None):  # noqa: F811
    """Convert BinaryField to String."""
    return graphene.String()


def execute_query(query, variables=None, request=None, user=None):
    """Execute a query from the ORM.

    Args:
        - query (str): String with GraphQL query.
        - variables (dict, optional): If the query has variables they need to be passed in as a dictionary.
        - request (django.test.client.RequestFactory, optional): Used to authenticate.
        - user (django.contrib.auth.models.User, optional): Used to authenticate.

    Returns:
        GraphQL Object: Result for query
    """
    if not request and not user:
        raise ValueError("Either request or username should be provided")
    if not request:
        request = RequestFactory().post("/graphql/")
        request.user = user
    backend = get_default_backend()
    schema = graphene_settings.SCHEMA
    document = backend.document_from_string(schema, query)
    if variables:
        return document.execute(context_value=request, variable_values=variables)
    else:
        return document.execute(context_value=request)


def execute_saved_query(saved_query_slug, **kwargs):
    """Execute saved query from the ORM.

    Args:
        - saved_query_slug (str): Slug of a saved GraphQL query.
        - variables (dict, optional): If the query has variables they need to be passed in as a dictionary.
        - request (django.test.client.RequestFactory, optional): Used to authenticate.
        - user (django.contrib.auth.models.User, optional): Used to authenticate.

    Returns:
        GraphQL Object: Result for query
    """
    query = GraphQLQuery.objects.get(slug=saved_query_slug)
    return execute_query(query=query.query, **kwargs)
