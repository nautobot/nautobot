from django.db.models import JSONField, BigIntegerField
from django.db.models.fields import BinaryField
from django.test.client import RequestFactory

from nautobot.extras.context_managers import web_request_context
from nautobot.extras.models import GraphQLQuery

import graphene
from graphene.types import generic
from graphene_django.converter import convert_django_field
from graphene_django.settings import graphene_settings
from graphql import get_default_backend
from graphql.language import ast


@convert_django_field.register(JSONField)
def convert_json(field, registry=None):
    """Convert JSONField to GenericScalar."""
    return generic.GenericScalar()


@convert_django_field.register(BinaryField)
def convert_binary(field, registry=None):
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


# See also:
# https://github.com/graphql-python/graphene-django/issues/241
# https://github.com/graphql-python/graphene/pull/1261 (graphene 3.0)
class BigInteger(graphene.types.Scalar):
    """An integer which, unlike GraphQL's native Int type, doesn't reject values outside (-2^31, 2^31-1).

    Currently only used for ASNField, which goes up to 2^32-1 (i.e., unsigned 32-bit int); it's possible
    that this approach may fail for values in excess of 2^53-1 (the largest integer value supported in JavaScript).
    """

    serialize = int
    parse_value = int

    @staticmethod
    def parse_literal(node):
        if isinstance(node, ast.IntValue):
            return int(node.value)


@convert_django_field.register(BigIntegerField)
def convert_biginteger(field, registry=None):
    """Convert BigIntegerField to BigInteger scalar."""
    return BigInteger()
