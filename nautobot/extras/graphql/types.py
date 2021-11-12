from graphene_django import DjangoObjectType

from nautobot.extras.models import Status, Tag
from nautobot.extras.filters import StatusFilterSet, TagFilterSet


class TagType(DjangoObjectType):
    """Graphql Type Object for Tag model."""

    class Meta:
        model = Tag
        filterset_class = TagFilterSet


class StatusType(DjangoObjectType):
    """Graphql Type object for `Status` model."""

    class Meta:
        model = Status
        filterset_class = StatusFilterSet
