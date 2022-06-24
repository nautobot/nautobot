from django.urls import path, include

from nautobot.dcim.views import CableCreateView, PathTraceView
from nautobot.extras.views import ObjectChangeLogView
from . import views
from .models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork

app_name = "circuits"
circuit_type_router = views.CircuitTypeRouter()
provider_router = views.ProviderRouter()
provider_network_router = views.ProviderNetworkRouter()
circuit_termination_router = views.CircuitTerminationRouter()
circuit_router = views.CircuitRouter()
circuit_type_router.register("circuit-types", views.CircuitTypeViewSet, basename="circuittype")
provider_router.register("providers", views.ProviderViewSet, basename="provider")
provider_network_router.register("provider-networks", views.ProviderNetworkViewSet, basename="providernetwork")
circuit_termination_router.register(
    "circuit-terminations", views.CircuitTerminationViewset, basename="circuittermination"
)
circuit_router.register("circuits", views.CircuitViewSet, basename="circuit")


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
    path(
        "circuit-terminations/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="circuittermination_changelog",
        kwargs={"model": CircuitTermination},
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
    path("", include(circuit_type_router.urls)),
    path("", include(provider_router.urls)),
    path("", include(provider_network_router.urls)),
    path("", include(circuit_termination_router.urls)),
    path("", include(circuit_router.urls)),
]
