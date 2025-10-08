from django.urls import path

from . import views

BASE_URL_TO_APP_LABEL = {}

# Initialize URL base, API, and admin URL patterns for plugins
apps_patterns = [
    path("installed-apps/", views.InstalledAppsView.as_view(), name="apps_list"),
    path("installed-apps/<str:app>/", views.InstalledAppDetailView.as_view(), name="app_detail"),
    path("marketplace/", views.MarketplaceView.as_view(), name="apps_marketplace"),
]
plugin_patterns = [  # 3.0 TODO: remove these
    path("installed-plugins/", views.InstalledAppsView.as_view(), name="plugins_list"),
    path("installed-plugins/<str:plugin>/", views.InstalledAppDetailView.as_view(), name="plugin_detail"),
]
apps_api_patterns = [
    path("", views.AppsAPIRootView.as_view(), name="api-root"),
    path("installed-apps/", views.InstalledAppsAPIView.as_view(), name="apps-list"),
]
plugin_api_patterns = [
    path("", views.AppsAPIRootView.as_view(), name="api-root"),
    path(
        "installed-plugins/",
        views.InstalledAppsAPIView.as_view(),
        name="plugins-list",
    ),
]
plugin_admin_patterns = []
