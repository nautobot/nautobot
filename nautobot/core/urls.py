from django.conf import settings
from django.conf.urls import include
from django.urls import path, re_path
from django.views.static import serve

from graphene_django.views import GraphQLView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from nautobot.core.api.views import APIRootView, StatusView, GraphQLDRFAPIView
from nautobot.core.views import HomeView, StaticMediaFailureView, SearchView
from nautobot.extras.plugins.urls import (
    plugin_admin_patterns,
    plugin_patterns,
    plugin_api_patterns,
)
from nautobot.users.views import LoginView, LogoutView
from .admin import admin_site


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

_patterns = [
    # Base views
    path("", HomeView.as_view(), name="home"),
    path("search/", SearchView.as_view(), name="search"),
    # Login/logout
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # Apps
    path("circuits/", include("nautobot.circuits.urls")),
    path("dcim/", include("nautobot.dcim.urls")),
    path("extras/", include("nautobot.extras.urls")),
    path("ipam/", include("nautobot.ipam.urls")),
    path("tenancy/", include("nautobot.tenancy.urls")),
    path("user/", include("nautobot.users.urls")),
    path("virtualization/", include("nautobot.virtualization.urls")),
    # API
    path("api/", APIRootView.as_view(), name="api-root"),
    path("api/circuits/", include("nautobot.circuits.api.urls")),
    path("api/dcim/", include("nautobot.dcim.api.urls")),
    path("api/extras/", include("nautobot.extras.api.urls")),
    path("api/ipam/", include("nautobot.ipam.api.urls")),
    path("api/tenancy/", include("nautobot.tenancy.api.urls")),
    path("api/users/", include("nautobot.users.api.urls")),
    path("api/virtualization/", include("nautobot.virtualization.api.urls")),
    path("api/status/", StatusView.as_view(), name="api-status"),
    path("api/docs/", schema_view.with_ui("swagger"), name="api_docs"),
    path("api/redoc/", schema_view.with_ui("redoc"), name="api_redocs"),
    re_path(
        r"^api/swagger(?P<format>.json|.yaml)$",
        schema_view.without_ui(),
        name="schema_swagger",
    ),
    # GraphQL
    path("graphql/", GraphQLView.as_view(graphiql=True), name="graphql"),
    path("api/graphql/", GraphQLDRFAPIView.as_view(), name="graphql-api"),
    # Serving static media in Django
    path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
    # Admin
    path("admin/", admin_site.urls),
    path("admin/background-tasks/", include("django_rq.urls")),
    # Errors
    path("media-failure/", StaticMediaFailureView.as_view(), name="media_failure"),
    # Plugins
    path("plugins/", include((plugin_patterns, "plugins"))),
    path("api/plugins/", include((plugin_api_patterns, "plugins-api"))),
    path("admin/plugins/", include(plugin_admin_patterns)),
]


if settings.DEBUG:
    import debug_toolbar

    _patterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]

if settings.METRICS_ENABLED:
    _patterns += [
        path("", include("django_prometheus.urls")),
    ]

if settings.SOCIAL_AUTH_ENABLED:
    _patterns += [
        path(
            "",
            include("social_django.urls", namespace=settings.SOCIAL_AUTH_URL_NAMESPACE),
        )
    ]

# Prepend BASE_PATH
urlpatterns = [path("{}".format(settings.BASE_PATH), include(_patterns))]

handler500 = "nautobot.core.views.server_error"
