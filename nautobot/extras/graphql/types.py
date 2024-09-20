from nautobot.core.graphql.types import OptimizedNautobotObjectType
from nautobot.extras.filters import (
    ContactAssociationFilterSet,
    DynamicGroupFilterSet,
    StatusFilterSet,
    TagFilterSet,
)
from nautobot.extras.models import ContactAssociation, DynamicGroup, Status, Tag


class ContactAssociationType(OptimizedNautobotObjectType):
    """GraphQL Type object for `ContactAssociation` model."""

    class Meta:
        model = ContactAssociation
        filterset_class = ContactAssociationFilterSet


class DynamicGroupType(OptimizedNautobotObjectType):
    """Graphql Type object for `DynamicGroup` model."""

    class Meta:
        model = DynamicGroup
        filterset_class = DynamicGroupFilterSet


class StatusType(OptimizedNautobotObjectType):
    """Graphql Type object for `Status` model."""

    class Meta:
        model = Status
        filterset_class = StatusFilterSet


class TagType(OptimizedNautobotObjectType):
    """Graphql Type Object for Tag model."""

    class Meta:
        model = Tag
        filterset_class = TagFilterSet
