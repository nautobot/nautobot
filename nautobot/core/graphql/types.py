import datetime

from django.contrib.contenttypes.models import ContentType
import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError


class OptimizedNautobotObjectType(DjangoObjectType):
    url = graphene.String()

    # IMPORTANT:
    # Do NOT override get_queryset here.
    #
    # In graphene-django 3.1.15 and later, customizing get_queryset changes how forward FK/1:1 fields are resolved
    # internally (it wraps FK resolvers in a custom resolver path that defeats gql optimizer hints),
    # which can re-introduce FK N+1 query regressions.
    #
    # Nautobot query optimization is handled explicitly by wrapping the *root* queryset with
    # `graphene_django_optimizer.query(...)` in our GraphQL resolvers.
    # See nautobot/core/graphql/generators.py for more details.
    #
    # Permission enforcement for ID/node lookups is handled in get_node().

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
