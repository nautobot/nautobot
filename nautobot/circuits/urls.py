from django.urls import path

from nautobot.dcim.views import CableCreateView, PathTraceView
from nautobot.extras.views import ObjectChangeLogView
from . import views
from .models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork

app_name = "circuits"
urlpatterns = [
    # Providers
    path("providers/", views.ProviderListView.as_view(), name="provider_list"),
    path("providers/add/", views.ProviderEditView.as_view(), name="provider_add"),
    path(
        "providers/import/",
        views.ProviderBulkImportView.as_view(),
        name="provider_import",
    ),
    path(
        "providers/edit/",
        views.ProviderBulkEditView.as_view(),
        name="provider_bulk_edit",
    ),
    path(
        "providers/delete/",
        views.ProviderBulkDeleteView.as_view(),
        name="provider_bulk_delete",
    ),
    path("providers/<slug:slug>/", views.ProviderView.as_view(), name="provider"),
    path(
        "providers/<slug:slug>/edit/",
        views.ProviderEditView.as_view(),
        name="provider_edit",
    ),
    path(
        "providers/<slug:slug>/delete/",
        views.ProviderDeleteView.as_view(),
        name="provider_delete",
    ),
    path(
        "providers/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="provider_changelog",
        kwargs={"model": Provider},
    ),
    path("provider-networks/", views.ProviderNetworkListView.as_view(), name="providernetwork_list"),
    path("provider-networks/add/", views.ProviderNetworkEditView.as_view(), name="providernetwork_add"),
    path("provider-networks/import/", views.ProviderNetworkBulkImportView.as_view(), name="providernetwork_import"),
    path("provider-networks/edit/", views.ProviderNetworkBulkEditView.as_view(), name="providernetwork_bulk_edit"),
    path(
        "provider-networks/delete/", views.ProviderNetworkBulkDeleteView.as_view(), name="providernetwork_bulk_delete"
    ),
    path("provider-networks/<slug:slug>/", views.ProviderNetworkView.as_view(), name="providernetwork"),
    path("provider-networks/<slug:slug>/edit/", views.ProviderNetworkEditView.as_view(), name="providernetwork_edit"),
    path(
        "provider-networks/<slug:slug>/delete/",
        views.ProviderNetworkDeleteView.as_view(),
        name="providernetwork_delete",
    ),
    path(
        "provider-networks/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="providernetwork_changelog",
        kwargs={"model": ProviderNetwork},
    ),
    # Circuit types
    path("circuit-types/", views.CircuitTypeListView.as_view(), name="circuittype_list"),
    path(
        "circuit-types/add/",
        views.CircuitTypeEditView.as_view(),
        name="circuittype_add",
    ),
    path(
        "circuit-types/import/",
        views.CircuitTypeBulkImportView.as_view(),
        name="circuittype_import",
    ),
    path(
        "circuit-types/delete/",
        views.CircuitTypeBulkDeleteView.as_view(),
        name="circuittype_bulk_delete",
    ),
    path(
        "circuit-types/<slug:slug>/",
        views.CircuitTypeView.as_view(),
        name="circuittype",
    ),
    path(
        "circuit-types/<slug:slug>/edit/",
        views.CircuitTypeEditView.as_view(),
        name="circuittype_edit",
    ),
    path(
        "circuit-types/<slug:slug>/delete/",
        views.CircuitTypeDeleteView.as_view(),
        name="circuittype_delete",
    ),
    path(
        "circuit-types/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="circuittype_changelog",
        kwargs={"model": CircuitType},
    ),
    # Circuits
    path("circuits/", views.CircuitListView.as_view(), name="circuit_list"),
    path("circuits/add/", views.CircuitEditView.as_view(), name="circuit_add"),
    path("circuits/import/", views.CircuitBulkImportView.as_view(), name="circuit_import"),
    path("circuits/edit/", views.CircuitBulkEditView.as_view(), name="circuit_bulk_edit"),
    path(
        "circuits/delete/",
        views.CircuitBulkDeleteView.as_view(),
        name="circuit_bulk_delete",
    ),
    path("circuits/<uuid:pk>/", views.CircuitView.as_view(), name="circuit"),
    path("circuits/<uuid:pk>/edit/", views.CircuitEditView.as_view(), name="circuit_edit"),
    path(
        "circuits/<uuid:pk>/delete/",
        views.CircuitDeleteView.as_view(),
        name="circuit_delete",
    ),
    path(
        "circuits/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="circuit_changelog",
        kwargs={"model": Circuit},
    ),
    path(
        "circuits/<uuid:pk>/terminations/swap/",
        views.CircuitSwapTerminations.as_view(),
        name="circuit_terminations_swap",
    ),
    # Circuit terminations
    path(
        "circuits/<uuid:circuit>/terminations/add/",
        views.CircuitTerminationEditView.as_view(),
        name="circuittermination_add",
    ),
    path("circuit-terminations/<uuid:pk>/", views.CircuitTerminationView.as_view(), name="circuittermination"),
    path(
        "circuit-terminations/<uuid:pk>/edit/",
        views.CircuitTerminationEditView.as_view(),
        name="circuittermination_edit",
    ),
    path(
        "circuit-terminations/<uuid:pk>/delete/",
        views.CircuitTerminationDeleteView.as_view(),
        name="circuittermination_delete",
    ),
    path(
        "circuit-terminations/<uuid:termination_a_id>/connect/<str:termination_b_type>/",
        CableCreateView.as_view(),
        name="circuittermination_connect",
        kwargs={"termination_a_type": CircuitTermination},
    ),
    path(
        "circuit-terminations/<uuid:pk>/trace/",
        PathTraceView.as_view(),
        name="circuittermination_trace",
        kwargs={"model": CircuitTermination},
    ),
    path(
        "circuit-terminations/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="circuittermination_changelog",
        kwargs={"model": CircuitTermination},
    ),
]
