import graphene_django_optimizer as gql_optimizer

from nautobot.core.models import Tag
from nautobot.extras.filters import DynamicGroupFilterSet, StatusFilterSet, TagFilterSet
from nautobot.extras.models import DynamicGroup, Status


class TagType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type Object for Tag model."""

    class Meta:
        model = Tag
        filterset_class = TagFilterSet


class StatusType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type object for `Status` model."""

    class Meta:
        model = Status
        filterset_class = StatusFilterSet


class DynamicGroupType(gql_optimizer.OptimizedDjangoObjectType):
    """Graphql Type object for `DynamicGroup` model."""

    class Meta:
        model = DynamicGroup
        filterset_class = DynamicGroupFilterSet
