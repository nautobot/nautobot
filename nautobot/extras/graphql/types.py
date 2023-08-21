from nautobot.core.graphql.types import OptimizedNautobotObjectType
from nautobot.extras.models import Status, Tag, DynamicGroup
from nautobot.extras.filters import StatusFilterSet, TagFilterSet, DynamicGroupFilterSet


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
