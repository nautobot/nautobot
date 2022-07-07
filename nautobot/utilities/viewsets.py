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
    def __init__(self, *args, **kwargs):
        if kwargs.get("suffix") == "List":
            self.action = "view"
            self.template_name = self.get_template_name("list")
            self.queryset = self.table_queryset()
        elif kwargs.get("suffix") == "Detail":
            self.action = "view"
            self.template_name = self.get_template_name("detail")
            self.queryset = self.detail_queryset()
        elif kwargs.get("suffix") == "Add":
            self.action = "add"
            self.template_name = self.get_template_name("edit")
            self.queryset = self.detail_queryset()
        elif kwargs.get("suffix") == "Import":
            self.action = "add"
            self.template_name = self.get_template_name("bulk_import")
            self.queryset = self.table_queryset()
        elif kwargs.get("suffix") == "Edit":
            self.action = "change"
            self.template_name = self.get_template_name("edit")
            self.queryset = self.detail_queryset()
        elif kwargs.get("suffix") == "Bulk Edit":
            self.action = "change"
            self.template_name = self.get_template_name("bulk_edit")
            self.queryset = self.table_queryset()
        elif kwargs.get("suffix") == "Delete":
            self.action = "delete"
            self.template_name = self.get_template_name("delete")
            self.queryset = self.detail_queryset()
        elif kwargs.get("suffix") == "Bulk Delete":
            self.action = "delete"
            self.template_name = self.get_template_name("bulk_delete")
            self.queryset = self.table_queryset()
        else:
            self.action = "view"
            self.template_name = self.get_template_name("list")
            self.queryset = self.detail_queryset()

        super().__init__(*args, **kwargs)

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, self.action)


class NautobotRouter(
    SimpleRouter,
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectEditViewMixin,
    ObjectDeleteViewMixin,
    BulkDeleteViewMixin,
    BulkEditViewMixin,
    BulkImportViewMixin,
):

    viewset = None
    exclude_views = []

    def __init__(self, prefix, basename):
        super().__init__()
        self.routes = super().define_routes()
        self.exclude_routes()
        self.register(prefix=prefix, viewset=self.viewset, basename=basename)

    def exclude_routes(self):
        for view in self.exclude_views:
            for route in self.routes:
                if view in route.name:
                    self.routes.remove(route)
                    break
