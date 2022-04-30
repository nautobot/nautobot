from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView

from nautobot.extras.views import ObjectChangeLogView

from example_plugin import views
from example_plugin.models import AnotherExampleModel, ExampleModel


app_name = "example_plugin"

urlpatterns = [
    path("", views.ExamplePluginHomeView.as_view(), name="home"),
    path("config/", views.ExamplePluginConfigView.as_view(), name="config"),
    path("models/", views.ExampleModelListView.as_view(), name="examplemodel_list"),
    path("models/add/", views.ExampleModelEditView.as_view(), name="examplemodel_add"),
    path(
        "models/edit/",
        views.ExampleModelBulkEditView.as_view(),
        name="examplemodel_bulk_edit",
    ),
    path(
        "models/delete/",
        views.ExampleModelBulkDeleteView.as_view(),
        name="examplemodel_bulk_delete",
    ),
    path(
        "models/import/",
        views.ExampleModelBulkImportView.as_view(),
        name="examplemodel_import",
    ),
    path("models/<uuid:pk>/", views.ExampleModelView.as_view(), name="examplemodel"),
    path(
        "models/<uuid:pk>/edit/",
        views.ExampleModelEditView.as_view(),
        name="examplemodel_edit",
    ),
    path(
        "models/<uuid:pk>/delete/",
        views.ExampleModelDeleteView.as_view(),
        name="examplemodel_delete",
    ),
    path(
        "models/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="examplemodel_changelog",
        kwargs={"model": ExampleModel},
    ),
    path("other-models/", views.AnotherExampleModelListView.as_view(), name="anotherexamplemodel_list"),
    path("other-models/add/", views.AnotherExampleModelEditView.as_view(), name="anotherexamplemodel_add"),
    path(
        "other-models/edit/",
        views.AnotherExampleModelBulkEditView.as_view(),
        name="anotherexamplemodel_bulk_edit",
    ),
    path(
        "other-models/delete/",
        views.AnotherExampleModelBulkDeleteView.as_view(),
        name="anotherexamplemodel_bulk_delete",
    ),
    path("other-models/<uuid:pk>/", views.AnotherExampleModelView.as_view(), name="anotherexamplemodel"),
    path(
        "other-models/<uuid:pk>/edit/",
        views.AnotherExampleModelEditView.as_view(),
        name="anotherexamplemodel_edit",
    ),
    path(
        "other-models/<uuid:pk>/delete/",
        views.AnotherExampleModelDeleteView.as_view(),
        name="anotherexamplemodel_delete",
    ),
    path(
        "other-models/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="anotherexamplemodel_changelog",
        kwargs={"model": AnotherExampleModel},
    ),
    path(
        "docs/",
        RedirectView.as_view(url=static("example_plugin/docs/index.html")),
        name="docs",
    ),
]
