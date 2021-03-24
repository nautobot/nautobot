from django.conf.urls import include
from django.urls import path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from nautobot.core.api.views import APIRootView, StatusView, GraphQLDRFAPIView
from nautobot.extras.plugins.urls import plugin_api_patterns


openapi_info = openapi.Info(
    title="Nautobot API",
    default_version="v2",
    description="API to access Nautobot",
    terms_of_service="https://github.com/nautobot/nautobot",
    license=openapi.License(name="Apache v2 License"),
)

schema_view = get_schema_view(
    openapi_info,
    validators=["flex", "ssv"],
    public=True,
)

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
    path("docs/", schema_view.with_ui("swagger"), name="api_docs"),
    path("redoc/", schema_view.with_ui("redoc"), name="api_redocs"),
    re_path(
        r"^swagger(?P<format>.json|.yaml)$",
        schema_view.without_ui(),
        name="schema_swagger",
    ),
    # GraphQL
    path("graphql/", GraphQLDRFAPIView.as_view(), name="graphql-api"),
    # Plugins
    path("plugins/", include((plugin_api_patterns, "plugins-api"))),
]
