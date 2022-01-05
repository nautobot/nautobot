from django.urls import path

from nautobot.extras.views import ObjectChangeLogView

from example_plugin import views
from example_plugin.models import DummyModel


app_name = "example_plugin"

urlpatterns = [
    path("", views.ExamplePluginHomeView.as_view(), name="home"),
    path("config/", views.ExamplePluginConfigView.as_view(), name="config"),
    path("models/", views.DummyModelListView.as_view(), name="dummymodel_list"),
    path("models/add/", views.DummyModelEditView.as_view(), name="dummymodel_add"),
    path(
        "models/edit/",
        views.DummyModelBulkEditView.as_view(),
        name="dummymodel_bulk_edit",
    ),
    path(
        "models/delete/",
        views.DummyModelBulkDeleteView.as_view(),
        name="dummymodel_bulk_delete",
    ),
    path(
        "models/import/",
        views.DummyModelBulkImportView.as_view(),
        name="dummymodel_import",
    ),
    path("models/<uuid:pk>/", views.DummyModelView.as_view(), name="dummymodel"),
    path(
        "models/<uuid:pk>/edit/",
        views.DummyModelEditView.as_view(),
        name="dummymodel_edit",
    ),
    path(
        "models/<uuid:pk>/delete/",
        views.DummyModelDeleteView.as_view(),
        name="dummymodel_delete",
    ),
    path(
        "models/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="dummymodel_changelog",
        kwargs={"model": DummyModel},
    ),
]
