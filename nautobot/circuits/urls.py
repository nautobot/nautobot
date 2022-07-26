from django.urls import path, include

from nautobot.dcim.views import CableCreateView, PathTraceView
from nautobot.extras.views import ObjectChangeLogView
from . import views
from .models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork

app_name = "circuits"
# circuit_type_router = views.CircuitTypeViewSetRouter(prefix="circuit_types", basename="circuittype")
# provider_router = views.ProviderViewSetRouter(prefix="providers", basename="provider")
# provider_network_router = views.ProviderNetworkViewSetRouter(prefix="provider-networks", basename="providernetwork")
circuit_termination_router = views.CircuitTerminationViewSetRouter(
    prefix="circuit-terminations", basename="circuittermination"
)
# circuit_router = views.CircuitViewSetRouter(prefix="circuits", basename="circuit")


urlpatterns = [
    path(
        "circuit-types/",
        views.CircuitTypeDRFViewSet.as_view({"get": "list"}),
        name="circuittype_list",
    ),
    path(
        "circuit-types/add/",
        views.CircuitTypeDRFViewSet.as_view({"get": "create_or_update", "post": "perform_create_or_update"}),
        name="circuittype_add",
    ),
    path(
        "circuit-types/delete/",
        views.CircuitTypeDRFViewSet.as_view({"get": "bulk_destroy", "post": "bulk_destroy"}),
        name="circuittype_bulk_delete",
    ),
    path(
        "circuit-types/import/",
        views.CircuitTypeDRFViewSet.as_view({"get": "bulk_create", "post": "perform_bulk_create"}),
        name="circuittype_import",
    ),
    path(
        "circuit-types/<slug:slug>/",
        views.CircuitTypeDRFViewSet.as_view({"get": "retrieve"}),
        name="circuittype",
    ),
    path(
        "circuit-types/<slug:slug>/edit/",
        views.CircuitTypeDRFViewSet.as_view({"get": "create_or_update", "post": "perform_create_or_update"}),
        name="circuittype_edit",
    ),
    path(
        "circuit-types/<slug:slug>/delete/",
        views.CircuitTypeDRFViewSet.as_view({"get": "destroy", "post": "perform_destroy"}),
        name="circuittype_delete",
    ),
    path(
        "providers/",
        views.ProviderDRFViewSet.as_view({"get": "list"}),
        name="provider_list",
    ),
    path(
        "providers/add/",
        views.ProviderDRFViewSet.as_view({"get": "create_or_update", "post": "perform_create_or_update"}),
        name="provider_add",
    ),
    path(
        "providers/edit/",
        views.ProviderDRFViewSet.as_view({"get": "bulk_edit", "post": "bulk_edit"}),
        name="provider_bulk_edit",
    ),
    path(
        "providers/delete/",
        views.ProviderDRFViewSet.as_view({"get": "bulk_destroy", "post": "bulk_destroy"}),
        name="provider_bulk_delete",
    ),
    path(
        "providers/import/",
        views.ProviderDRFViewSet.as_view({"get": "bulk_create", "post": "perform_bulk_create"}),
        name="provider_import",
    ),
    path(
        "providers/<slug:slug>/",
        views.ProviderDRFViewSet.as_view({"get": "retrieve"}),
        name="provider",
    ),
    path(
        "providers/<slug:slug>/edit/",
        views.ProviderDRFViewSet.as_view({"get": "create_or_update", "post": "perform_create_or_update"}),
        name="provider_edit",
    ),
    path(
        "providers/<slug:slug>/delete/",
        views.ProviderDRFViewSet.as_view({"get": "destroy", "post": "perform_destroy"}),
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
        views.ProviderNetworkDRFViewSet.as_view({"get": "create_or_update", "post": "perform_create_or_update"}),
        name="providernetwork_add",
    ),
    path(
        "provider-networks/edit/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "bulk_edit", "post": "bulk_edit"}),
        name="providernetwork_bulk_edit",
    ),
    path(
        "provider-networks/delete/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "bulk_destroy", "post": "bulk_destroy"}),
        name="providernetwork_bulk_delete",
    ),
    path(
        "provider-networks/import/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "bulk_create", "post": "perform_bulk_create"}),
        name="providernetwork_import",
    ),
    path(
        "provider-networks/<slug:slug>/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "retrieve"}),
        name="providernetwork",
    ),
    path(
        "provider-networks/<slug:slug>/edit/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "create_or_update", "post": "perform_create_or_update"}),
        name="providernetwork_edit",
    ),
    path(
        "provider-networks/<slug:slug>/delete/",
        views.ProviderNetworkDRFViewSet.as_view({"get": "destroy", "post": "perform_destroy"}),
        name="providernetwork_delete",
    ),
    path(
        "provider-networks/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="providernetwork_changelog",
        kwargs={"model": ProviderNetwork},
    ),
    path(
        "circuit-types/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="circuittype_changelog",
        kwargs={"model": CircuitType},
    ),
    path(
        "circuit-terminations/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="circuittermination_changelog",
        kwargs={"model": CircuitTermination},
    ),
    path(
        "circuits/",
        views.CircuitDRFViewSet.as_view({"get": "list"}),
        name="circuit_list",
    ),
    path(
        "circuits/add/",
        views.CircuitDRFViewSet.as_view({"get": "create_or_update", "post": "perform_create_or_update"}),
        name="circuit_add",
    ),
    path(
        "circuits/edit/",
        views.CircuitDRFViewSet.as_view({"get": "bulk_edit", "post": "bulk_edit"}),
        name="circuit_bulk_edit",
    ),
    path(
        "circuits/delete/",
        views.CircuitDRFViewSet.as_view({"get": "bulk_destroy", "post": "bulk_destroy"}),
        name="circuit_bulk_delete",
    ),
    path(
        "circuits/import/",
        views.CircuitDRFViewSet.as_view({"get": "bulk_create", "post": "perform_bulk_create"}),
        name="circuit_import",
    ),
    path(
        "circuits/<uuid:pk>/",
        views.CircuitDRFViewSet.as_view({"get": "retrieve"}),
        name="circuit",
    ),
    path(
        "circuits/<uuid:pk>/edit/",
        views.CircuitDRFViewSet.as_view({"get": "create_or_update", "post": "perform_create_or_update"}),
        name="circuit_edit",
    ),
    path(
        "circuits/<uuid:pk>/delete/",
        views.CircuitDRFViewSet.as_view({"get": "destroy", "post": "perform_destroy"}),
        name="circuit_delete",
    ),
    path(
        "circuits/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="circuit_changelog",
        kwargs={"model": Circuit},
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
        "circuits/<uuid:pk>/terminations/swap/",
        views.CircuitSwapTerminations.as_view(),
        name="circuit_terminations_swap",
    ),
    # path("", include(circuit_type_router.urls)),
    # path("", include(provider_router.urls)),
    # path("", include(provider_network_router.urls)),
    path("", include(circuit_termination_router.urls)),
    # path("", include(circuit_router.urls)),
]
