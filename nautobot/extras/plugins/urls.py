from django.apps import apps
from django.conf import settings
from django.conf.urls import include
from django.urls import path

from nautobot.extras.plugins.utils import import_object

from . import views

# Initialize URL base, API, and admin URL patterns for plugins
plugin_patterns = [
    path("installed-plugins/", views.InstalledPluginsView.as_view(), name="plugins_list"),
    path("installed-plugins/<str:plugin>/", views.InstalledPluginDetailView.as_view(), name="plugin_detail"),
]
plugin_api_patterns = [
    path("", views.PluginsAPIRootView.as_view(), name="api-root"),
    path(
        "installed-plugins/",
        views.InstalledPluginsAPIView.as_view(),
        name="plugins-list",
    ),
]
plugin_admin_patterns = []

# Register base/API URL patterns for each plugin
for plugin_path in settings.PLUGINS:
    plugin_name = plugin_path.split(".")[-1]
    app = apps.get_app_config(plugin_name)
    base_url = app.base_url or app.label

    # Check if the plugin specifies any base URLs
    urlpatterns = import_object(f"{plugin_path}.urls.urlpatterns")
    if urlpatterns is not None:
        plugin_patterns.append(path(f"{base_url}/", include((urlpatterns, app.label))))

    # Check if the plugin specifies any API URLs
    urlpatterns = import_object(f"{plugin_path}.api.urls.urlpatterns")
    if urlpatterns is not None:
        plugin_api_patterns.append(path(f"{base_url}/", include((urlpatterns, f"{app.label}-api"))))
