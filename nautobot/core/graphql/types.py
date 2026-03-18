import datetime

from django.contrib.contenttypes.models import ContentType
import graphene
from graphene_django import DjangoObjectType
import graphene_django_optimizer as gql_optimizer
from graphql import GraphQLError


class OptimizedNautobotObjectType(gql_optimizer.OptimizedDjangoObjectType):
    url = graphene.String()

    # Reset get_queryset to DjangoObjectType's base implementation.
    # OptimizedDjangoObjectType overrides get_queryset for auto-optimization, but in graphene-django 3.x
    # any get_queryset override causes FK field resolvers to be wrapped in a custom_resolver that the
    # optimizer cannot introspect, preventing it from adding select_related for FK fields and causing
    # N+1 query regressions. Query optimization is handled explicitly via gql_optimizer.query() calls
    # in the list and single-item resolvers, so this auto-optimization is not needed.
    get_queryset = classmethod(DjangoObjectType.get_queryset.__func__)

    @classmethod
    def get_node(cls, info, id):  # pylint: disable=redefined-builtin
        """Override get_node to enforce object-level permissions.

        We intentionally do NOT override get_queryset (see above), so permission
        enforcement for Relay-style node lookups and any plugin code that calls
        get_node() is handled here instead.
        """
        queryset = cls._meta.model.objects.all()
        if hasattr(queryset, "restrict"):
            queryset = queryset.restrict(info.context.user, "view")
        try:
            return queryset.get(pk=id)
        except cls._meta.model.DoesNotExist:
            return None

    def resolve_url(self, info):
        return self.get_absolute_url(api=True)  # pylint: disable=no-member

    class Meta:
        abstract = True


class ContentTypeType(OptimizedNautobotObjectType):
    """
    Graphene-Django object type for ContentType records.

    Needed because ContentType is a built-in model, not one that we own and can auto-generate types for.
    """

    class Meta:
        model = ContentType


class DateType(graphene.Date):
    """
    Overriding the default serialize method from https://github.com/graphql-python/graphene/blob/master/graphene/types/datetime.py
    to handle the case where the date object is passed as a str object.
    """

    @staticmethod
    def serialize(date):
        if isinstance(date, datetime.datetime):
            date = date.date()
            return date.isoformat()
        elif isinstance(date, datetime.date):
            return date.isoformat()
        elif isinstance(date, str):
            return date
        else:
            raise GraphQLError(f'Received not compatible date "{date!r}"')


class JSON(graphene.Scalar):
    @staticmethod
    def serialize_data(dt):
        return dt

    serialize = serialize_data
    parse_value = serialize_data
    parse_literal = serialize_data
