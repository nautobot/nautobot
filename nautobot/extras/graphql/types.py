import graphene
from graphene_django.converter import convert_django_field

from taggit.managers import TaggableManager

from nautobot.core.graphql.base import NautobotObjectType
from nautobot.extras.models import Status, Tag
from nautobot.extras.filters import StatusFilterSet, TagFilterSet


class TagType(NautobotObjectType):
    """Graphql Type Object for Tag model."""

    class Meta:
        model = Tag
        filterset_class = TagFilterSet


@convert_django_field.register(TaggableManager)
def convert_field_to_list_tags(field, registry=None):
    """Convert TaggableManager to List of Tags."""
    return graphene.List(TagType)


class StatusType(NautobotObjectType):
    """Graphql Type object for `Status` model."""

    class Meta:
        model = Status
        filterset_class = StatusFilterSet
