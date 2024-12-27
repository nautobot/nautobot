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
from nautobot.core.views.generic import GenericView
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.extras.plugins.tables import InstalledAppsTable


def load_marketplace_data():
    file_path = os.path.dirname(os.path.abspath(__file__)) + "/marketplace_manifest.yml"
    with open(file_path, "r") as yamlfile:
        marketplace_data = yaml.safe_load(yamlfile)

    return marketplace_data


def get_app_headline(package_name, description, marketplace_data):
    """If the given package_name is in the marketplace_data, use its headline there; else use the given description."""
    for marketplace_app in marketplace_data["apps"]:
        if marketplace_app["package_name"] == package_name and marketplace_app["headline"]:
            return marketplace_app["headline"]
    return description


class InstalledAppsView(GenericView):
    """
    View for listing all installed Apps.
    """

    table = InstalledAppsTable

    def get(self, request):
        marketplace_data = load_marketplace_data()
        app_configs = apps.get_app_configs()
        data = []
        for app in app_configs:
            if app.name in settings.PLUGINS:
                try:
                    reverse(app.home_view_name)
                    home_url = app.home_view_name
                except NoReverseMatch:
                    home_url = None
                try:
                    reverse(app.config_view_name)
                    config_url = app.config_view_name
                except NoReverseMatch:
                    config_url = None
                try:
                    reverse(app.docs_view_name)
                    docs_url = app.docs_view_name
                except NoReverseMatch:
                    docs_url = None
                data.append(
                    {
                        "name": app.verbose_name,
                        "package_name": app.name,
                        "app_label": app.label,
                        "author": app.author,
                        "author_email": app.author_email,
                        "description": get_app_headline(app.name, app.description, marketplace_data),
                        "version": app.version,
                        "actions": {
                            "home": home_url,
                            "configure": config_url,
                            "docs": docs_url,
                        },
                    }
                )
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
                "object": app_config,
                "headline": get_app_headline(app_config.name, app_config.description, load_marketplace_data()),
            },
        )


class InstalledAppsAPIView(NautobotAPIVersionMixin, APIView):
    """
    API view for listing all installed non-core Apps.
    """

    permission_classes = [permissions.IsAdminUser]

    def get_view_name(self):
        return "Installed Apps"

    @staticmethod
    def _get_app_data(app_config, marketplace_data):
        try:
            home_url = reverse(app_config.home_view_name)
        except NoReverseMatch:
            home_url = None
        try:
            config_url = reverse(app_config.config_view_name)
        except NoReverseMatch:
            config_url = None
        try:
            docs_url = reverse(app_config.docs_view_name)
        except NoReverseMatch:
            docs_url = None
        return {
            "name": app_config.verbose_name,
            "package": app_config.name,
            "author": app_config.author,
            "author_email": app_config.author_email,
            "description": get_app_headline(app_config.name, app_config.headline, marketplace_data),
            "version": app_config.version,
            "home_url": home_url,
            "config_url": config_url,
            "docs_url": docs_url,
        }

    @extend_schema(exclude=True)
    def get(self, request, format=None):  # pylint: disable=redefined-builtin
        marketplace_data = load_marketplace_data()
        return Response([self._get_app_data(apps.get_app_config(app), marketplace_data) for app in settings.PLUGINS])


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
    def get(self, request, format=None):  # pylint: disable=redefined-builtin
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

    def get(self, request):
        marketplace_data = load_marketplace_data()

        installed_apps = [app for app in apps.get_app_configs() if app.name in settings.PLUGINS]

        # Flag already installed apps
        for installed_app in installed_apps:
            for marketplace_app in marketplace_data["apps"]:
                if installed_app.name == marketplace_app["package_name"]:
                    marketplace_app["installed"] = True
                    break

        return render(request, "extras/marketplace.html", {"apps": marketplace_data["apps"]})
