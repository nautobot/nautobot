from django.urls import path

from nautobot.core.models.dynamic_groups import DynamicGroup
from nautobot.core import views
from nautobot.extras import views as extras_views

app_name = "core"
urlpatterns = [
    # Dynamic Groups
    path("dynamic-groups/", views.DynamicGroupListView.as_view(), name="dynamicgroup_list"),
    path("dynamic-groups/add/", views.DynamicGroupEditView.as_view(), name="dynamicgroup_add"),
    path(
        "dynamic-groups/delete/",
        views.DynamicGroupBulkDeleteView.as_view(),
        name="dynamicgroup_bulk_delete",
    ),
    path("dynamic-groups/<str:slug>/", views.DynamicGroupView.as_view(), name="dynamicgroup"),
    path("dynamic-groups/<str:slug>/edit/", views.DynamicGroupEditView.as_view(), name="dynamicgroup_edit"),
    path("dynamic-groups/<str:slug>/delete/", views.DynamicGroupDeleteView.as_view(), name="dynamicgroup_delete"),
    path(
        "dynamic-groups/<str:slug>/changelog/",
        extras_views.ObjectChangeLogView.as_view(),
        name="dynamicgroup_changelog",
        kwargs={"model": DynamicGroup},
    ),
    path(
        "dynamic-groups/<str:slug>/notes/",
        extras_views.ObjectNotesView.as_view(),
        name="dynamicgroup_notes",
        kwargs={"model": DynamicGroup},
    ),
]
