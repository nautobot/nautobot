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
    GetMenuAPIView,
    GetObjectCountsView,
    GetSettingsView,
    GraphQLDRFAPIView,
    NautobotSpectacularSwaggerView,
    NautobotSpectacularRedocView,
    NewUIReadyRoutesAPIView,
    StatusView,
)
from nautobot.extras.plugins.urls import plugin_api_patterns

core_api_patterns = [
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
ui_api_patterns = [
    # Lookup Expr
    path("core/", include((core_api_patterns, "core-api"))),
    path("new-ui-ready-routes/", NewUIReadyRoutesAPIView.as_view(), name="new-ui-ready-routes"),
    path("get-menu/", GetMenuAPIView.as_view(), name="get-menu"),
    path("get-object-counts/", GetObjectCountsView.as_view(), name="get-object-counts"),
    path("settings/", GetSettingsView.as_view(), name="settings"),
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
    # Core, keeping for backwards compatibility of the legacy UI (Dynamic Filter Form)
    path("core/", include((core_api_patterns, "core-api"))),
    # UI
    path("ui/", include((ui_api_patterns, "ui-api"))),
]
