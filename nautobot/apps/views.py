"""Utilities for apps to implement UI views."""

from nautobot.core.views.generic import GenericView, ObjectView
from nautobot.core.views.mixins import (
    ObjectBulkCreateViewMixin,
    ObjectBulkDestroyViewMixin,
    ObjectBulkUpdateViewMixin,
    ObjectChangeLogViewMixin,
    ObjectDestroyViewMixin,
    ObjectDetailViewMixin,
    ObjectEditViewMixin,
    ObjectListViewMixin,
    ObjectNotesViewMixin,
)
from nautobot.core.views.viewsets import NautobotUIViewSet

__all__ = (
    "GenericView",
    "NautobotUIViewSet",
    "ObjectBulkCreateViewMixin",
    "ObjectBulkDestroyViewMixin",
    "ObjectBulkUpdateViewMixin",
    "ObjectChangeLogViewMixin",
    "ObjectDestroyViewMixin",
    "ObjectDetailViewMixin",
    "ObjectEditViewMixin",
    "ObjectListViewMixin",
    "ObjectNotesViewMixin",
    "ObjectView",
)
