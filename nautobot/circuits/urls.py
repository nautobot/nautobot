from django.urls import path, include

from nautobot.dcim.views import CableCreateView, PathTraceView
from nautobot.extras.views import ObjectChangeLogView
from . import views
from .models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork

app_name = "circuits"
circuit_type_router = views.CircuitTypeRouter()
circuit_type_router.register("circuit-types", views.CircuitTypeViewSet, basename="circuittype")
provider_router = views.ProviderRouter()
provider_router.register("providers", views.ProviderViewSet, basename="provider")
provider_network_router = views.ProviderNetworkRouter()
provider_network_router.register("provider-networks", views.ProviderNetworkViewSet, basename="providernetwork")

urlpatterns = [
    path(
        "providers/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="provider_changelog",
        kwargs={"model": Provider},
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
    path("", include(circuit_type_router.urls)),
    path("", include(provider_router.urls)),
    path("", include(provider_network_router.urls)),
]
