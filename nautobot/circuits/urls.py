from django.urls import path

from nautobot.dcim.views import CableCreateView, PathTraceView
from nautobot.extras.views import ObjectChangeLogView, ObjectNotesView
from . import views
from .models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork

from rest_framework.routers import Route, SimpleRouter


class DRFViewSetRouter(SimpleRouter):
    """
    Django Rest Framework ViewSet Custom Router.
    """

    routes = [
        Route(
            url=r"^{prefix}$",
            mapping={"get": "list"},
            name="{basename}_list",
            detail=False,
            initkwargs={"suffix": "List"},
        ),
        Route(
            url=r"^{prefix}/add/$",
            mapping={
                "get": "create",
                "post": "create",
            },
            name="{basename}_add",
            detail=False,
            initkwargs={"suffix": "Add"},
        ),
        Route(
            url=r"^{prefix}/import/$",
            mapping={
                "get": "bulk_create",
                "post": "bulk_create",
            },
            name="{basename}_import",
            detail=False,
            initkwargs={"suffix": "Import"},
        ),
        Route(
            url=r"^{prefix}/edit/$",
            mapping={
                "post": "bulk_update",
            },
            name="{basename}_bulk_edit",
            detail=False,
            initkwargs={"suffix": "Bulk Edit"},
        ),
        Route(
            url=r"^{prefix}/delete/$",
            mapping={
                "post": "bulk_destroy",
            },
            name="{basename}_bulk_delete",
            detail=False,
            initkwargs={"suffix": "Bulk Delete"},
        ),
        Route(
            url=r"^{prefix}/{lookup}$",
            mapping={"get": "retrieve"},
            name="{basename}",
            detail=True,
            initkwargs={"suffix": "Detail"},
        ),
        Route(
            url=r"^{prefix}/{lookup}/delete/$",
            mapping={
                "get": "destroy",
                "post": "destroy",
            },
            name="{basename}_delete",
            detail=True,
            initkwargs={"suffix": "Delete"},
        ),
        Route(
            url=r"^{prefix}/{lookup}/edit/$",
            mapping={
                "get": "update",
                "post": "update",
            },
            name="{basename}_edit",
            detail=True,
            initkwargs={"suffix": "Edit"},
        ),
    ]

    def exclude_urls(self, excluded_urls):
        """
        Helper function to remove any urls that are not included in the viewset or need to be re-initialized.
        """
        for url in self.urls:
            if url.name in excluded_urls:
                self.urls.remove(url)


app_name = "circuits"
router = DRFViewSetRouter()
router.register("providers", views.ProviderDRFViewSet, basename="provider")
router.register("provider-networks", views.ProviderNetworkDRFViewSet, basename="providernetwork")
router.register("circuit-types", views.CircuitTypeDRFViewSet, basename="circuittype")
router.register("circuits", views.CircuitDRFViewSet, basename="circuit")
router.register("circuit-terminations", views.CircuitTerminationDRFViewset, basename="circuittermination")
excluded_urls = ["circuittype_bulk_edit"]
router.exclude_urls(excluded_urls)

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
        "provider-networks/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="providernetwork_notes",
        kwargs={"model": ProviderNetwork},
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
        views.CircuitTerminationDRFViewset.as_view({"get": "create", "post": "create"}),
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
