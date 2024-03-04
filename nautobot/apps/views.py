"""Utilities for apps to implement UI views."""

from nautobot.core.views.generic import (
    BulkComponentCreateView,
    BulkCreateView,
    BulkDeleteView,
    BulkEditView,
    BulkImportView,  # 3.0 TODO: deprecated, will be removed in 3.0
    BulkRenameView,
    ComponentCreateView,
    ObjectDeleteView,
    ObjectEditView,
    ObjectImportView,
    ObjectListView,
    ObjectView,
)
from nautobot.core.views.mixins import (
    AdminRequiredMixin,
    ContentTypePermissionRequiredMixin,
    GetReturnURLMixin,
    NautobotViewSetMixin,
    ObjectBulkCreateViewMixin,  # 3.0 TODO: deprecated, will be removed in 3.0
    ObjectBulkDestroyViewMixin,
    ObjectBulkUpdateViewMixin,
    ObjectChangeLogViewMixin,
    ObjectDestroyViewMixin,
    ObjectDetailViewMixin,
    ObjectEditViewMixin,
    ObjectListViewMixin,
    ObjectNotesViewMixin,
    ObjectPermissionRequiredMixin,
)
from nautobot.core.views.paginator import EnhancedPage, EnhancedPaginator, get_paginate_count
from nautobot.core.views.renderers import NautobotHTMLRenderer
from nautobot.core.views.utils import (
    check_filter_for_display,
    csv_format,
    get_csv_form_fields_from_serializer_class,
    handle_protectederror,
    prepare_cloned_fields,
)
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.extras.views import check_and_call_git_repository_function, ObjectDynamicGroupsView, ObjectNotesView

__all__ = (
    "AdminRequiredMixin",
    "BulkComponentCreateView",
    "BulkCreateView",
    "BulkDeleteView",
    "BulkEditView",
    "BulkImportView",  # 3.0 TODO: remove this
    "BulkRenameView",
    "check_and_call_git_repository_function",
    "check_filter_for_display",
    "ComponentCreateView",
    "ContentTypePermissionRequiredMixin",
    "csv_format",
    "EnhancedPage",
    "EnhancedPaginator",
    "get_csv_form_fields_from_serializer_class",
    "get_paginate_count",
    "GetReturnURLMixin",
    "handle_protectederror",
    "NautobotHTMLRenderer",
    "NautobotUIViewSet",
    "NautobotViewSetMixin",
    "ObjectBulkCreateViewMixin",  # 3.0 TODO: remove this
    "ObjectBulkDestroyViewMixin",
    "ObjectBulkUpdateViewMixin",
    "ObjectChangeLogViewMixin",
    "ObjectDeleteView",
    "ObjectDestroyViewMixin",
    "ObjectDetailViewMixin",
    "ObjectDynamicGroupsView",
    "ObjectEditView",
    "ObjectEditViewMixin",
    "ObjectImportView",
    "ObjectListView",
    "ObjectListViewMixin",
    "ObjectNotesView",
    "ObjectNotesViewMixin",
    "ObjectPermissionRequiredMixin",
    "ObjectView",
    "prepare_cloned_fields",
)
