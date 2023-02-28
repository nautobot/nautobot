from django.conf.urls import include
from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularJSONAPIView,
    SpectacularYAMLAPIView,
)

from nautobot.core.api.views import (
    APIRootView,
    GetFilterSetFieldDOMElementAPIView,
    GetFilterSetFieldLookupExpressionChoicesAPIView,
    GetMenu,
    GraphQLDRFAPIView,
    SetCSRFCookie, StatusView,
    NautobotSpectacularSwaggerView,
    NautobotSpectacularRedocView,
)
from nautobot.extras.plugins.urls import plugin_api_patterns


# TODO: these should be moved under `api/ui/` for consistency. See #3240.
core_api_patterns = [
    # Lookup Expr
    path(
        "filterset-fields/lookup-choices/",
        GetFilterSetFieldLookupExpressionChoicesAPIView.as_view(),
        name="filtersetfield-list-lookupchoices",
    ),
    path(
        "filterset-fields/lookup-value-dom-element/",
        GetFilterSetFieldDOMElementAPIView.as_view(),
        name="filtersetfield-retrieve-lookupvaluedomelement",
    ),
]

urlpatterns = [
    # Base views
    path("", APIRootView.as_view(), name="api-root"),
    path("circuits/", include("nautobot.circuits.api.urls")),
    path("dcim/", include("nautobot.dcim.api.urls")),
    path("extras/", include("nautobot.extras.api.urls")),
    path("ipam/", include("nautobot.ipam.api.urls")),
    path("tenancy/", include("nautobot.tenancy.api.urls")),
    path("users/", include("nautobot.users.api.urls")),
    path("virtualization/", include("nautobot.virtualization.api.urls")),
    path("status/", StatusView.as_view(), name="api-status"),
    path("docs/", NautobotSpectacularSwaggerView.as_view(url_name="schema"), name="api_docs"),
    path("redoc/", NautobotSpectacularRedocView.as_view(url_name="schema"), name="api_redocs"),
    path("swagger/", SpectacularAPIView.as_view(), name="schema"),
    path("swagger.json", SpectacularJSONAPIView.as_view(), name="schema_json"),
    path("swagger.yaml", SpectacularYAMLAPIView.as_view(), name="schema_yaml"),
    # GraphQL
    path("graphql/", GraphQLDRFAPIView.as_view(), name="graphql-api"),
    # Plugins
    path("plugins/", include((plugin_api_patterns, "plugins-api"))),
    # TODO: get-menu should be moved under `api/ui/`, not root-level as here. See #3240.
    # Core Apps
    path("get-menu/", GetMenu.as_view(), name="get-menu"),
    path("get-csrf/", SetCSRFCookie.as_view(), name="get-csrf"),
    # Core
    path("core/", include((core_api_patterns, "core-api"))),
]
