import datetime

from django.contrib.contenttypes.models import ContentType
import graphene
import graphene_django_optimizer as gql_optimizer


class OptimizedNautobotObjectType(gql_optimizer.OptimizedDjangoObjectType):
    url = graphene.String()

    def resolve_url(self, info):
        return self.get_absolute_url(api=True)

    class Meta:
        abstract = True


class ContentTypeType(OptimizedNautobotObjectType):
    """
    Graphene-Django object type for ContentType records.

    Needed because ContentType is a built-in model, not one that we own and can auto-generate types for.
    """

    class Meta:
        model = ContentType


class Date(graphene.Date):
    """
    Overriding the default serialize method from https://github.com/graphql-python/graphene/blob/master/graphene/types/datetime.py
    to handle the case where the date object is passed as a str object.
    """

    @staticmethod
    def serialize(date):
        if isinstance(date, datetime.datetime):
            date = date.date()
        if not isinstance(date, datetime.date) and isinstance(date, str):
            date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        if not isinstance(date, datetime.date):
            raise AssertionError('Received not compatible date "{}"'.format(repr(date)))
        return date.isoformat()


class JSON(graphene.Scalar):
    @staticmethod
    def serialize_data(dt):
        return dt

    serialize = serialize_data
    parse_value = serialize_data
    parse_literal = serialize_data
