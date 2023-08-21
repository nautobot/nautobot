import graphene
from graphene_django import DjangoObjectType
import graphene_django_optimizer as gql_optimizer

from nautobot.extras.models import Status, Tag, DynamicGroup
from nautobot.extras.filters import StatusFilterSet, TagFilterSet, DynamicGroupFilterSet


class NautobotObjectType(DjangoObjectType):
    url = graphene.String()

    def resolve_url(self, args):
        return self.get_absolute_url()

    class Meta:
        abstract = True


class OptimizedNautobotObjectType(gql_optimizer.OptimizedDjangoObjectType):
    url = graphene.String()

    def resolve_url(self, args):
        return self.get_absolute_url()

    class Meta:
        abstract = True


class TagType(OptimizedNautobotObjectType):
    """Graphql Type Object for Tag model."""

    class Meta:
        model = Tag
        filterset_class = TagFilterSet


class StatusType(OptimizedNautobotObjectType):
    """Graphql Type object for `Status` model."""

    class Meta:
        model = Status
        filterset_class = StatusFilterSet


class DynamicGroupType(OptimizedNautobotObjectType):
    """Graphql Type object for `DynamicGroup` model."""

    class Meta:
        model = DynamicGroup
        filterset_class = DynamicGroupFilterSet
