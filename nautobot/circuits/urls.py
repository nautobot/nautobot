from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.dcim.views import CableCreateView, PathTraceView
from nautobot.extras.views import ObjectChangeLogView, ObjectNotesView
from . import views
from .models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork


app_name = "circuits"
router = NautobotUIViewSetRouter()
router.register("providers", views.ProviderUIViewSet)
router.register("provider-networks", views.ProviderNetworkUIViewSet)
router.register("circuit-types", views.CircuitTypeUIViewSet)
router.register("circuits", views.CircuitUIViewSet)
router.register("circuit-terminations", views.CircuitTerminationUIViewSet)

urlpatterns = [
    path(
        "providers/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="provider_changelog",
        kwargs={"model": Provider},
    ),
    path(
        "providers/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="provider_notes",
        kwargs={"model": Provider},
    ),
    path(
        "provider-networks/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="providernetwork_changelog",
        kwargs={"model": ProviderNetwork},
    ),
    path(
        "provider-networks/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="providernetwork_notes",
        kwargs={"model": ProviderNetwork},
    ),
    path(
        "circuit-types/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="circuittype_changelog",
        kwargs={"model": CircuitType},
    ),
    path(
        "circuit-types/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="circuittype_notes",
        kwargs={"model": CircuitType},
    ),
    path(
        "circuits/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="circuit_changelog",
        kwargs={"model": Circuit},
    ),
    path(
        "circuits/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="circuit_notes",
        kwargs={"model": Circuit},
    ),
    path(
        "circuits/<uuid:pk>/terminations/swap/",
        views.CircuitSwapTerminations.as_view(),
        name="circuit_terminations_swap",
    ),
    path(
        "circuits/<uuid:circuit>/terminations/add/",
        views.CircuitTerminationUIViewSet.as_view({"get": "create", "post": "create"}),
        name="circuittermination_add",
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
    path(
        "circuit-terminations/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="circuittermination_notes",
        kwargs={"model": CircuitTermination},
    ),
]
urlpatterns += router.urls
