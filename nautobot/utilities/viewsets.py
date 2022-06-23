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

from django.template.loader import select_template, TemplateDoesNotExist


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
            self.template_name = self.get_template_name("list")
            self.queryset = self.table_queryset
        elif kwargs.get("suffix") == "Detail":
            self.action = "view"
            self.template_name = self.get_template_name("detail")
            self.queryset = self.detail_queryset
        elif kwargs.get("suffix") == "Add":
            self.action = "add"
            self.template_name = self.get_template_name("edit")
            self.queryset = self.detail_queryset
        elif kwargs.get("suffix") == "Import":
            self.action = "add"
            self.template_name = self.get_template_name("bulk_import")
            self.queryset = self.table_queryset
        elif kwargs.get("suffix") == "Edit":
            self.action = "change"
            self.template_name = self.get_template_name("edit")
            self.queryset = self.detail_queryset
        elif kwargs.get("suffix") == "Bulk Edit":
            self.action = "change"
            self.template_name = self.get_template_name("bulk_edit")
            self.queryset = self.table_queryset
        elif kwargs.get("suffix") == "Delete":
            self.action = "delete"
            self.template_name = self.get_template_name("delete")
            self.queryset = self.detail_queryset
        elif kwargs.get("suffix") == "Bulk Delete":
            self.action = "delete"
            self.template_name = self.get_template_name("bulk_delete")
            self.queryset = self.table_queryset
        else:
            self.action = "view"
            self.template_name = self.get_template_name("list")
            self.queryset = self.detail_queryset

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

        # if self.table:
        #     if not self.object_list_table:
        #         self.object_list_table = self.table
        #     if not self.bulk_import_table:
        #         self.bulk_import_table = self.table
        #     if not self.bulk_edit_table:
        #         self.bulk_edit_table = self.table
        #     if not self.bulk_delete_table:
        #         self.bulk_delete_table = self.table

        super().__init__(*args, **kwargs)

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, self.action)

    def get_template_name(self, view_type):
        # Use "<app>/<model>_<view_type> if available, else fall back to generic templates
        model_opts = self.model._meta
        app_label = model_opts.app_label
        if view_type == "detail":
            return f"{app_label}/{model_opts.model_name}.html"

        try:
            select_template([f"{app_label}/{model_opts.model_name}_{view_type}.html"])
            return f"{app_label}/{model_opts.model_name}_{view_type}.html"
        except TemplateDoesNotExist:
            return f"generic/object_{view_type}.html"


class NautobotRouter(SimpleRouter, NautobotRouterMixin):
    def __init__(self):
        self.define_routes()
        super().__init__()
