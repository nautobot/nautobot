from nautobot.utilities.permissions import get_permission_for_model
from nautobot.utilities.views import (
    ObjectPermissionRequiredMixin,
    ObjectDetailViewMixin,
    ObjectDeleteViewMixin,
    ObjectListViewMixin,
    ObjectEditViewMixin,
    BulkImportViewMixin,
    BulkDeleteViewMixin,
    BulkEditViewMixin,
    View,
)
from rest_framework.routers import Route, SimpleRouter
from rest_framework.viewsets import ViewSetMixin


class NautobotViewSet(
    ObjectPermissionRequiredMixin,
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectEditViewMixin,
    ObjectDeleteViewMixin,
    BulkDeleteViewMixin,
    BulkEditViewMixin,
    BulkImportViewMixin,
    ViewSetMixin,
    View,
):
    queryset = None

    action_map = {
        "object_detail": {
            "queryset": "object_detail_queryset",
            "action": "view",
        },
        "object_list": {
            "queryset": "object_list_queryset",
            "action": "view",
        },
        "object_edit": {
            "queryset": "object_edit_queryset",
            "action": "change",  # could be set to "add" based on request context
        },
        "object_delete": {
            "queryset": "object_delete_queryset",
            "action": "delete",
        },
        "bulk_edit": {
            "queryset": "bulk_edit_queryset",
            "action": "change",
        },
        "bulk_import": {
            "queryset": "bulk_import_queryset",
            "action": "add",
        },
        "bulk_delete": {
            "queryset": "bulk_delete_queryset",
            "action": "delete",
        },
    }

    def __init__(self, *args, **kwargs):
        if self.queryset:
            if not self.object_detail_queryset:
                self.object_detail_queryset = self.queryset
            if not self.object_list_queryset:
                self.object_list_queryset = self.queryset
            if not self.object_edit_queryset:
                self.object_edit_queryset = self.queryset
            if not self.object_delete_queryset:
                self.object_delete_queryset = self.queryset
            if not self.bulk_import_queryset:
                self.bulk_import_queryset = self.queryset
            if not self.bulk_edit_queryset:
                self.bulk_edit_queryset = self.queryset
            if not self.bulk_delete_queryset:
                self.bulk_delete_queryset = self.queryset
        super().__init__(*args, **kwargs)

    def get_queryset_for_action(self, action):
        return self.action_map[action]["queryset"]

    def get_required_permission(self):
        return get_permission_for_model(self.get_queryset_for_action(self.action).model)


class NautobotRouter(SimpleRouter):
    routes = [
        Route(
            url=r"^{prefix}/$",
            mapping={
                "get": "handle_object_list_get",
            },
            name="{basename}_list",
            detail=False,
            initkwargs={"suffix": "List"},
        ),
        Route(
            url=r"^{prefix}/add/$",
            mapping={
                "get": "handle_object_edit_get",
                "post": "handle_object_edit_post",
            },
            name="{basename}_add",
            detail=False,
            initkwargs={"suffix": "Add"},
        ),
        Route(
            url=r"^{prefix}/import/$",
            mapping={
                "get": "handle_bulk_import_get",
                "post": "handle_bulk_import_post",
            },
            name="{basename}_import",
            detail=False,
            initkwargs={"suffix": "Import"},
        ),
        Route(
            url=r"^{prefix}/edit/$",
            mapping={
                "get": "handle_bulk_edit_get",
                "post": "handle_bulk_edit_post",
            },
            name="{basename}_bulk_edit",
            detail=False,
            initkwargs={"suffix": "Bulk Edit"},
        ),
        Route(
            url=r"^{prefix}/delete/$",
            mapping={
                "get": "handle_bulk_delete_get",
                "post": "handle_bulk_delete_post",
            },
            name="{basename}_bulk_delete",
            detail=False,
            initkwargs={"suffix": "Bulk Delete"},
        ),
        Route(
            url=r"^{prefix}/{lookup}/$",
            mapping={
                "get": "handle_object_detail_get",
            },
            name="{basename}",
            detail=True,
            initkwargs={"suffix": "Detail"},
        ),
        Route(
            url=r"^{prefix}/{lookup}/edit/$",
            mapping={
                "get": "handle_object_edit_get",
                "post": "handle_object_edit_post",
            },
            name="{basename}_edit",
            detail=True,
            initkwargs={"suffix": "Edit"},
        ),
        Route(
            url=r"^{prefix}/{lookup}/edit/$",
            mapping={
                "get": "handle_object_delete_get",
                "post": "handle_object_delete_post",
            },
            name="{basename}_delete",
            detail=True,
            initkwargs={"suffix": "Delete"},
        ),
    ]
