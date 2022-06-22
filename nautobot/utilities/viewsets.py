from nautobot.utilities.permissions import get_permission_for_model
from nautobot.utilities.views import (
    NautobotRouterMixin,
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
from rest_framework.routers import SimpleRouter
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
    form = None
    table = None
    filterset = None
    filterset_form = None

    def __init__(self, *args, **kwargs):
        if kwargs.get("suffix") == "List":
            self.action = "view"
        elif kwargs.get("suffix") == "Detail":
            self.action = "view"
        elif kwargs.get("suffix") == "Add" or kwargs.get("suffix") == "Import":
            self.action = "add"
        elif kwargs.get("suffix") == "Edit" or kwargs.get("suffix") == "Bulk Edit":
            self.action = "change"
        elif kwargs.get("suffix") == "Delete" or kwargs.get("suffix") == "Bulk Delete":
            self.action = "delete"
        else:
            self.action = "view"

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

        if self.form:
            if not self.object_edit_model_form:
                self.object_edit_model_form = self.form
            if not self.bulk_import_model_form:
                self.bulk_import_model_form = self.form
            if not self.bulk_edit_form:
                self.bulk_edit_form = self.form

        if self.filterset:
            if not self.object_list_filterset:
                self.object_list_filterset = self.filterset
            if not self.bulk_edit_filterset:
                self.bulk_edit_filterset = self.filterset

        if self.filterset_form:
            if not self.object_list_filterset_form:
                self.object_list_filterset_form = self.filterset_form

        if self.table:
            if not self.object_list_table:
                self.object_list_table = self.table
            if not self.bulk_import_table:
                self.bulk_import_table = self.table
            if not self.bulk_edit_table:
                self.bulk_edit_table = self.table
            if not self.bulk_delete_table:
                self.bulk_delete_table = self.table

        super().__init__(*args, **kwargs)

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, self.action)


class NautobotRouter(SimpleRouter, NautobotRouterMixin):
    def __init__(self):
        self.define_routes()
        super().__init__()
