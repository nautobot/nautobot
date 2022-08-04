from django.urls import path

from nautobot.dcim.views import CableCreateView, PathTraceView
from nautobot.extras.views import ObjectChangeLogView
from . import views
from .models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork

app_name = "circuits"

urlpatterns = [
    path(
        "providers/",
        views.ProviderDRFViewSet.as_view({"get": "list"}),
        name="provider_list",
    ),
    path(
        "providers/add/",
        views.ProviderDRFViewSet.as_view({"get": "create_or_update", "post": "create_or_update"}),
        name="provider_add",
    ),
    path(
        "providers/import/",
        views.ProviderDRFViewSet.as_view({"get": "bulk_create", "post": "bulk_create"}),
        name="provider_import",
    ),
    path(
        "providers/edit/",
        views.ProviderDRFViewSet.as_view({"post": "bulk_update"}),
        name="provider_bulk_edit",
    ),
    path(
        "providers/delete/",
        views.ProviderDRFViewSet.as_view({"get": "bulk_destroy", "post": "bulk_destroy"}),
        name="provider_bulk_delete",
    ),
    path(
        "providers/<slug:slug>/",
        views.ProviderDRFViewSet.as_view({"get": "retrieve"}),
        name="provider",
    ),
    path(
        "providers/<slug:slug>/edit/",
        views.ProviderDRFViewSet.as_view({"get": "create_or_update", "post": "create_or_update"}),
        name="provider_edit",
    ),
    path(
        "providers/<slug:slug>/delete/",
        views.ProviderDRFViewSet.as_view({"get": "destroy", "post": "destroy"}),
        name="provider_delete",
    ),
    path(
        "providers/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="provider_changelog",
        kwargs={"model": Provider},
    ),
    path(
        "provider-networks/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "list"}),
        name="providernetwork_list",
    ),
    path(
        "provider-networks/add/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "create_or_update", "post": "create_or_update"}),
        name="providernetwork_add",
    ),
    path(
        "provider-networks/import/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "bulk_create", "post": "bulk_create"}),
        name="providernetwork_import",
    ),
    path(
        "provider-networks/edit/",
        views.ProviderNetworkDRFViewSet.as_view({"post": "bulk_update"}),
        name="providernetwork_bulk_edit",
    ),
    path(
        "provider-networks/delete/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "bulk_destroy", "post": "bulk_destroy"}),
        name="providernetwork_bulk_delete",
    ),
    path(
        "provider-networks/<slug:slug>/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "retrieve"}),
        name="providernetwork",
    ),
    path(
        "provider-networks/<slug:slug>/edit/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "create_or_update", "post": "create_or_update"}),
        name="providernetwork_edit",
    ),
    path(
        "provider-networks/<slug:slug>/delete/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "destroy", "post": "destroy"}),
        name="providernetwork_delete",
    ),
    path(
        "provider-networks/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="providernetwork_changelog",
        kwargs={"model": ProviderNetwork},
    ),
    path(
        "circuit-types/",
        views.CircuitTypeDRFViewSet.as_view({"get": "list"}),
        name="circuittype_list",
    ),
    path(
        "circuit-types/add/",
        views.CircuitTypeDRFViewSet.as_view({"get": "create_or_update", "post": "create_or_update"}),
        name="circuittype_add",
    ),
    path(
        "circuit-types/import/",
        views.CircuitTypeDRFViewSet.as_view({"get": "bulk_create", "post": "bulk_create"}),
        name="circuittype_import",
    ),
    path(
        "circuit-types/delete/",
        views.CircuitTypeDRFViewSet.as_view({"get": "bulk_destroy", "post": "bulk_destroy"}),
        name="circuittype_bulk_delete",
    ),
    path(
        "circuit-types/<slug:slug>/",
        views.CircuitTypeDRFViewSet.as_view({"get": "retrieve"}),
        name="circuittype",
    ),
    path(
        "circuit-types/<slug:slug>/edit/",
        views.CircuitTypeDRFViewSet.as_view({"get": "create_or_update", "post": "create_or_update"}),
        name="circuittype_edit",
    ),
    path(
        "circuit-types/<slug:slug>/delete/",
        views.CircuitTypeDRFViewSet.as_view({"get": "destroy", "post": "destroy"}),
        name="circuittype_delete",
    ),
    path(
        "circuit-types/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="circuittype_changelog",
        kwargs={"model": CircuitType},
    ),
    path(
        "circuits/",
        views.CircuitDRFViewSet.as_view({"get": "list"}),
        name="circuit_list",
    ),
    path(
        "circuits/add/",
        views.CircuitDRFViewSet.as_view({"get": "create_or_update", "post": "create_or_update"}),
        name="circuit_add",
    ),
    path(
        "circuits/import/",
        views.CircuitDRFViewSet.as_view({"get": "bulk_create", "post": "bulk_create"}),
        name="circuit_import",
    ),
    path(
        "circuits/edit/",
        views.CircuitDRFViewSet.as_view({"post": "bulk_update"}),
        name="circuit_bulk_edit",
    ),
    path(
        "circuits/delete/",
        views.CircuitDRFViewSet.as_view({"get": "bulk_destroy", "post": "bulk_destroy"}),
        name="circuit_bulk_delete",
    ),
    path(
        "circuits/<uuid:pk>/",
        views.CircuitDRFViewSet.as_view({"get": "retrieve"}),
        name="circuit",
    ),
    path(
        "circuits/<uuid:pk>/edit/",
        views.CircuitDRFViewSet.as_view({"get": "create_or_update", "post": "create_or_update"}),
        name="circuit_edit",
    ),
    path(
        "circuits/<uuid:pk>/delete/",
        views.CircuitDRFViewSet.as_view({"get": "destroy", "post": "destroy"}),
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
    path(
        "circuits/<uuid:circuit>/terminations/add/",
        views.CircuitTerminationDRFViewset.as_view({"get": "create_or_update", "post": "create_or_update"}),
        name="circuittermination_add",
    ),
    path(
        "circuit-terminations/<uuid:pk>/",
        views.CircuitTerminationDRFViewset.as_view({"get": "retrieve"}),
        name="circuittermination",
    ),
    path(
        "circuit-terminations/<uuid:pk>/edit/",
        views.CircuitTerminationDRFViewset.as_view({"get": "create_or_update", "post": "create_or_update"}),
        name="circuittermination_edit",
    ),
    path(
        "circuit-terminations/<uuid:pk>/delete/",
        views.CircuitTerminationDRFViewset.as_view({"get": "destroy", "post": "destroy"}),
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
