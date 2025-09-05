from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.urls import include, path
from django.views.generic import TemplateView

from nautobot.core.views import (
    AboutView,
    CustomGraphQLView,
    get_file_with_authorization,
    HomeView,
    MediaView,
    NautobotMetricsView,
    NautobotMetricsViewAuth,
    RenderJinjaView,
    SearchView,
    StaticMediaFailureView,
    ThemePreviewView,
    WorkerStatusView,
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
    path("about/", AboutView.as_view(), name="about"),
    path("search/", SearchView.as_view(), name="search"),
    # Login/logout
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # Apps
    path("circuits/", include("nautobot.circuits.urls")),
    path("cloud/", include("nautobot.cloud.urls")),
    path("dcim/", include("nautobot.dcim.urls")),
    path("extras/", include("nautobot.extras.urls")),
    path("ipam/", include("nautobot.ipam.urls")),
    path("tenancy/", include("nautobot.tenancy.urls")),
    # TODO: deprecate this url and use users
    path("user/", include("nautobot.users.urls")),
    path("users/", include("nautobot.users.urls", "users")),
    path("virtualization/", include("nautobot.virtualization.urls")),
    path("wireless/", include("nautobot.wireless.urls")),
    # API
    path("api/", include("nautobot.core.api.urls")),
    # GraphQL
    path("graphql/", CustomGraphQLView.as_view(graphiql=True), name="graphql"),
    # Serving static media in Django (TODO: should be DEBUG mode only - "This view is NOT hardened for production use")
    path("media/<path:path>", MediaView.as_view(), name="media"),
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
    path(
        "files/download/",
        get_file_with_authorization,
        {"add_attachment_headers": True},
        name="db_file_storage.download_file",
    ),
    # Celery worker status page
    path("worker-status/", WorkerStatusView.as_view(), name="worker_status"),
    # Jinja template renderer tool
    path("render-jinja-template/", RenderJinjaView.as_view(), name="render_jinja_template"),
    # Templated css file
    path(
        "template.css", TemplateView.as_view(template_name="template.css", content_type="text/css"), name="template_css"
    ),
    # The response is conditional as opposed to wrapping the path() call in an if statement to be able to test the setting with current test setup
    path(
        "robots.txt",
        lambda x: HttpResponse("User-Agent: *\nDisallow: /", content_type="text/plain")
        if settings.PUBLISH_ROBOTS_TXT
        else HttpResponseNotFound(),
        name="robots_txt",
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
