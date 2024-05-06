from django.conf import settings
from django.conf.urls import include, url
from django.urls import path
from django.views.generic import TemplateView
from django.views.static import serve

from nautobot.core.views import (
    CustomGraphQLView,
    get_file_with_authorization,
    HomeView,
    NautobotMetricsView,
    NautobotMetricsViewAuth,
    SearchView,
    StaticMediaFailureView,
    ThemePreviewView,
)
from nautobot.extras.plugins.urls import (
    apps_patterns,
    plugin_admin_patterns,
    plugin_patterns,
)
from nautobot.users.views import LoginView, LogoutView

from .admin import admin_site

urlpatterns = [
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
    path("api/", include("nautobot.core.api.urls")),
    # GraphQL
    path("graphql/", CustomGraphQLView.as_view(graphiql=True), name="graphql"),
    # Serving static media in Django (TODO: should be DEBUG mode only - "This view is NOT hardened for production use")
    path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
    # Admin
    path("admin/", admin_site.urls),
    # Errors
    path("media-failure/", StaticMediaFailureView.as_view(), name="media_failure"),
    # Apps
    path("apps/", include((apps_patterns, "apps"))),
    path("plugins/", include((plugin_patterns, "plugins"))),
    path("admin/plugins/", include(plugin_admin_patterns)),
    # Social auth/SSO
    path("", include("social_django.urls", namespace="social")),
    # django-health-check
    path(r"health/", include("health_check.urls")),
    # FileProxy attachments download/get URLs used in admin views only
    url(
        "files/download/",
        get_file_with_authorization,
        {"add_attachment_headers": True},
        name="db_file_storage.download_file",
    ),
    # Templated css file
    path(
        "template.css", TemplateView.as_view(template_name="template.css", content_type="text/css"), name="template_css"
    ),
]


if settings.DEBUG:
    try:
        import debug_toolbar

        urlpatterns += [
            path("__debug__/", include(debug_toolbar.urls)),
            path("theme-preview/", ThemePreviewView.as_view(), name="theme_preview"),
        ]
    except ImportError:
        pass

if settings.METRICS_ENABLED:
    if settings.METRICS_AUTHENTICATED:
        urlpatterns += [
            path("metrics/", NautobotMetricsViewAuth.as_view(), name="metrics"),
        ]
    else:
        urlpatterns += [
            path("metrics/", NautobotMetricsView.as_view(), name="metrics"),
        ]

handler404 = "nautobot.core.views.resource_not_found"
handler500 = "nautobot.core.views.server_error"

urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
