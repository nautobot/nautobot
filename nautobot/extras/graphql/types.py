import graphene

from nautobot.core.graphql.types import OptimizedNautobotObjectType
from nautobot.extras.filters import (
    ContactAssociationFilterSet,
    DynamicGroupFilterSet,
    JobFilterSet,
    ObjectLockFilterSet,
    ScheduledJobFilterSet,
    StatusFilterSet,
    TagFilterSet,
)
from nautobot.extras.models import ContactAssociation, DynamicGroup, Job, ObjectLock, ScheduledJob, Status, Tag


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


class JobType(OptimizedNautobotObjectType):
    """Graphql Type Object for Job model."""

    class Meta:
        model = Job
        filterset_class = JobFilterSet

    task_queues = graphene.List(graphene.String)


class ScheduledJobType(OptimizedNautobotObjectType):
    """Graphql Type Object for Job model."""

    class Meta:
        model = ScheduledJob
        filterset_class = ScheduledJobFilterSet

    queue = graphene.String


class StatusType(OptimizedNautobotObjectType):
    """Graphql Type object for `Status` model."""

    class Meta:
        model = Status
        filterset_class = StatusFilterSet


class ObjectLockType(OptimizedNautobotObjectType):
    """GraphQL Type object for the `ObjectLock` model."""

    class Meta:
        model = ObjectLock
        filterset_class = ObjectLockFilterSet
        # Explicit allow-list so a field added to ObjectLock later is not auto-exposed via GraphQL.
        fields = [
            "id",
            "content_type",
            "object_id",
            "prevent_delete",
            "prevent_update",
            "locked_fields",
            "reason",
            "source_context",
            "source_detail",
            "source_key",
            "created_by",
            "expires",
            "created",
            "last_updated",
        ]


class TagType(OptimizedNautobotObjectType):
    """Graphql Type Object for Tag model."""

    class Meta:
        model = Tag
        filterset_class = TagFilterSet
