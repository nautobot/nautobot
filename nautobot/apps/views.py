"""Utilities for apps to implement UI views."""

from nautobot.core.views.generic import ObjectView
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
