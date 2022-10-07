from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView

from nautobot.extras.views import ObjectChangeLogView, ObjectDynamicGroupsView, ObjectNotesView

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
    path(
        "models/<uuid:pk>/dynamic-groups/",
        ObjectDynamicGroupsView.as_view(),
        name="examplemodel_dynamicgroups",
        kwargs={"model": ExampleModel},
    ),
    path(
        "models/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="examplemodel_notes",
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
        "other-models/<uuid:pk>/dynamic-groups/",
        ObjectDynamicGroupsView.as_view(),
        name="anotherexamplemodel_dynamicgroups",
        kwargs={"model": AnotherExampleModel},
    ),
    path(
        "other-models/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="anotherexamplemodel_notes",
        kwargs={"model": AnotherExampleModel},
    ),
    path(
        "docs/",
        RedirectView.as_view(url=static("example_plugin/docs/index.html")),
        name="docs",
    ),
    path(
        "circuits/<uuid:pk>/example-plugin-tab/", views.CircuitDetailPluginTabView.as_view(), name="circuit_detail_tab"
    ),
    path(
        "devices/<uuid:pk>/example-plugin-tab-1/",
        views.DeviceDetailPluginTabOneView.as_view(),
        name="device_detail_tab_1",
    ),
    path(
        "devices/<uuid:pk>/example-plugin-tab-2/",
        views.DeviceDetailPluginTabTwoView.as_view(),
        name="device_detail_tab_2",
    ),
    # This URL definition is here in order to test the override_views functionality which is defined
    # in examples.plugin_with_view_override.plugin_with_view_override.views
    path("override-target/", views.ViewToBeOverridden.as_view(), name="view_to_be_overridden"),
]
