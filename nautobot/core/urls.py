from django.conf import settings
from django.conf.urls import include
from django.urls import path
from django.views.static import serve

from nautobot.core.views import CustomGraphQLView, HomeView, StaticMediaFailureView, SearchView
from nautobot.extras.plugins.urls import (
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
    # Serving static media in Django
    path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
    # Admin
    path("admin/", admin_site.urls),
    path("admin/background-tasks/", include("django_rq.urls")),
    # Errors
    path("media-failure/", StaticMediaFailureView.as_view(), name="media_failure"),
    # Plugins
    path("plugins/", include((plugin_patterns, "plugins"))),
    path("admin/plugins/", include(plugin_admin_patterns)),
    # Social auth/SSO
    path("", include("social_django.urls", namespace="social")),
    # django-health-check
    path(r"health/", include("health_check.urls")),
    # FileProxy attachments download/get URLs used in admin views only
    path("files/", include("db_file_storage.urls")),
]


if settings.DEBUG:
    try:
        import debug_toolbar

        urlpatterns += [
            path("__debug__/", include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass

if settings.METRICS_ENABLED:
    urlpatterns += [
        path("", include("django_prometheus.urls")),
    ]

handler404 = "nautobot.core.views.resource_not_found"
handler500 = "nautobot.core.views.server_error"
