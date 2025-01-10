from typing import Union

from django.apps import apps
from django.conf import settings
from django.conf.urls import include
from django.urls import path, URLPattern, URLResolver

from nautobot.extras.plugins.utils import import_object

from . import views

# Initialize URL base, API, and admin URL patterns for plugins
apps_patterns: list[Union[URLPattern, URLResolver]] = [
    path("installed-apps/", views.InstalledAppsView.as_view(), name="apps_list"),
    path("installed-apps/<str:app>/", views.InstalledAppDetailView.as_view(), name="app_detail"),
    path("marketplace/", views.MarketplaceView.as_view(), name="apps_marketplace"),
]
plugin_patterns: list[Union[URLPattern, URLResolver]] = [  # 3.0 TODO: remove these
    path("installed-plugins/", views.InstalledAppsView.as_view(), name="plugins_list"),
    path("installed-plugins/<str:plugin>/", views.InstalledAppDetailView.as_view(), name="plugin_detail"),
]
apps_api_patterns: list[Union[URLPattern, URLResolver]] = [
    path("", views.AppsAPIRootView.as_view(), name="api-root"),
    path("installed-apps/", views.InstalledAppsAPIView.as_view(), name="apps-list"),
]
plugin_api_patterns: list[Union[URLPattern, URLResolver]] = [
    path("", views.AppsAPIRootView.as_view(), name="api-root"),
    path(
        "installed-plugins/",
        views.InstalledAppsAPIView.as_view(),
        name="plugins-list",
    ),
]

# Register base/API URL patterns for each plugin
for plugin_path in settings.PLUGINS:
    plugin_name = plugin_path.split(".")[-1]
    app = apps.get_app_config(plugin_name)
    base_url = getattr(app, "base_url", None) or app.label

    # Check if the plugin specifies any base URLs
    urlpatterns = import_object(f"{plugin_path}.urls.urlpatterns")
    if urlpatterns is not None:
        plugin_patterns.append(path(f"{base_url}/", include((urlpatterns, app.label))))

    # Check if the plugin specifies any API URLs
    urlpatterns = import_object(f"{plugin_path}.api.urls.urlpatterns")
    if urlpatterns is not None:
        plugin_api_patterns.append(path(f"{base_url}/", include((urlpatterns, f"{app.label}-api"))))
