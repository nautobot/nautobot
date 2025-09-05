from collections import OrderedDict
import os

from django.apps import apps
from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.urls.exceptions import NoReverseMatch
from django_tables2 import RequestConfig
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
import yaml

from nautobot.core.api.views import AuthenticatedAPIRootView, NautobotAPIVersionMixin
from nautobot.core.forms import TableConfigForm
from nautobot.core.ui.breadcrumbs import Breadcrumbs, ViewNameBreadcrumbItem
from nautobot.core.ui.titles import Titles
from nautobot.core.views.generic import GenericView
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.extras.plugins.tables import InstalledAppsTable


def load_marketplace_data():
    file_path = os.path.dirname(os.path.abspath(__file__)) + "/marketplace_manifest.yml"
    with open(file_path, "r") as yamlfile:
        marketplace_data = yaml.safe_load(yamlfile)

    return marketplace_data


def override_app_data_with_marketplace_data(package_name, app_data, marketplace_data):
    """If the given package_name is in the marketplace_data, update/replace the app_data with marketplace_data."""
    for marketplace_app in marketplace_data["apps"]:
        if marketplace_app["package_name"] != package_name:
            continue
        for key in "author", "description", "headline", "availability", "name":
            if marketplace_app.get(key, None):
                app_data[key] = marketplace_app[key]
        break
    return app_data


def extract_app_data(app_config, marketplace_data):
    if app_config.name not in settings.PLUGINS:
        return None
    try:
        reverse(app_config.home_view_name)
        home_url = app_config.home_view_name
    except NoReverseMatch:
        home_url = None
    try:
        reverse(app_config.config_view_name)
        config_url = app_config.config_view_name
    except NoReverseMatch:
        config_url = None
    try:
        reverse(app_config.docs_view_name)
        docs_url = app_config.docs_view_name
    except NoReverseMatch:
        docs_url = None
    return override_app_data_with_marketplace_data(
        app_config.name,
        {
            "name": app_config.verbose_name,
            "package": app_config.name,
            "app_label": app_config.label,
            "author": app_config.author,
            "author_email": app_config.author_email,
            "description": app_config.description,
            "headline": app_config.description,
            "version": app_config.version,
            "home_url": home_url,
            "config_url": config_url,
            "docs_url": docs_url,
        },
        marketplace_data,
    )


class InstalledAppsView(GenericView):
    """
    View for listing all installed Apps.
    """

    table = InstalledAppsTable
    breadcrumbs = Breadcrumbs(
        items={"generic": [ViewNameBreadcrumbItem(view_name="apps:apps_list", label="Installed Apps")]}
    )
    view_titles = Titles(titles={"generic": "Installed Apps"})

    def get(self, request):
        marketplace_data = load_marketplace_data()
        app_configs = apps.get_app_configs()
        data = []
        for app_config in app_configs:
            if app_data := extract_app_data(app_config, marketplace_data):
                data.append(app_data)
        table = self.table(data, user=request.user)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(table)

        app_icons = {app["package_name"]: app.get("icon") for app in marketplace_data["apps"]}

        # Determine user's preferred display
        if self.request.GET.get("display") in ["list", "tiles"]:
            display = self.request.GET.get("display")
            if self.request.user.is_authenticated:
                self.request.user.set_config("extras.apps_list.display", display, commit=True)
        elif self.request.user.is_authenticated:
            display = self.request.user.get_config("extras.apps_list.display", "list")
        else:
            display = "list"

        return render(
            request,
            "extras/plugins_list.html",
            {
                "table": table,
                "table_config_form": TableConfigForm(table=table),
                # Using `None` as `table_template` falls back to default `responsive_table.html`.
                "table_template": "extras/plugins_tiles.html" if display == "tiles" else None,
                "filter_form": None,
                "app_icons": app_icons,
                "display": display,
                "view_action": "generic",
                "breadcrumbs": self.breadcrumbs,
                "view_titles": self.view_titles,
            },
        )


class InstalledAppDetailView(GenericView):
    """
    View for showing details of an installed App.
    """

    def get(self, request, app=None, plugin=None):
        if plugin and not app:
            app = plugin
        app_config = apps.get_app_config(app)
        if app_config.name not in settings.PLUGINS:
            raise Http404

        return render(
            request,
            "extras/plugin_detail.html",
            {
                "app_data": extract_app_data(app_config, load_marketplace_data()),
                "object": app_config,
            },
        )


class InstalledAppsAPIView(NautobotAPIVersionMixin, APIView):
    """
    API view for listing all installed non-core Apps.
    """

    permission_classes = [permissions.IsAdminUser]

    def get_view_name(self):
        return "Installed Apps"

    @extend_schema(exclude=True)
    def get(self, request, format=None):  # pylint: disable=redefined-builtin
        marketplace_data = load_marketplace_data()
        return Response([extract_app_data(apps.get_app_config(app), marketplace_data) for app in settings.PLUGINS])


class AppsAPIRootView(AuthenticatedAPIRootView):
    name = "Apps"
    description = "API extension point for installed Nautobot Apps"

    @staticmethod
    def _get_app_entry(app_config, request, format_):
        # Check if the App specifies any API URLs
        api_app_name = f"{app_config.name}-api"
        try:
            entry = (
                app_config.base_url or app_config.label,
                reverse(
                    f"plugins-api:{api_app_name}:api-root",
                    request=request,
                    format=format_,
                ),
            )
        except NoReverseMatch:
            # The App does not include an api-root url
            entry = None

        return entry

    @extend_schema(exclude=True)
    def get(self, request, *args, format=None, **kwargs):  # pylint: disable=redefined-builtin
        entries = []
        for app_name in settings.PLUGINS:
            app_config = apps.get_app_config(app_name)
            entry = self._get_app_entry(app_config, request, format)
            if entry is not None:
                entries.append(entry)

        if "apps" in request.path:
            return Response(
                OrderedDict(
                    (
                        (
                            "installed-apps",
                            reverse("apps-api:apps-list", request=request, format=format),
                        ),
                        *entries,
                    )
                )
            )

        return Response(
            OrderedDict(
                (
                    (
                        "installed-plugins",
                        reverse("plugins-api:plugins-list", request=request, format=format),
                    ),
                    *entries,
                )
            )
        )


class MarketplaceView(GenericView):
    """
    View for listing all available Apps.
    """

    breadcrumbs = Breadcrumbs(
        items={"generic": [ViewNameBreadcrumbItem(view_name="apps:apps_marketplace", label="Apps Marketplace")]}
    )
    view_titles = Titles(titles={"generic": "Apps Marketplace"})

    def get(self, request):
        marketplace_data = load_marketplace_data()

        installed_apps = [app for app in apps.get_app_configs() if app.name in settings.PLUGINS]

        # Flag already installed apps
        for installed_app in installed_apps:
            for marketplace_app in marketplace_data["apps"]:
                if installed_app.name == marketplace_app["package_name"]:
                    marketplace_app["installed"] = True
                    break

        return render(
            request,
            "extras/marketplace.html",
            {
                "apps": marketplace_data["apps"],
                "view_action": "generic",
                "breadcrumbs": self.breadcrumbs,
                "view_titles": self.view_titles,
            },
        )
