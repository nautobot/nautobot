from django.db.models import JSONField, BigIntegerField
from django.db.models.fields import BinaryField

import graphene
from graphene.types import generic
from graphene_django.converter import convert_django_field
from graphql.language import ast


@convert_django_field.register(JSONField)
def convert_json(field, registry=None):
    """Convert JSONField to GenericScalar."""
    return generic.GenericScalar()


@convert_django_field.register(BinaryField)
def convert_binary(field, registry=None):
    """Convert BinaryField to String."""
    return graphene.String()


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
