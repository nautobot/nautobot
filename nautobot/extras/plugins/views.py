from collections import OrderedDict

from django.apps import apps
from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.urls.exceptions import NoReverseMatch
from django.views.generic import View
from django_tables2 import RequestConfig
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from nautobot.core.api.views import AuthenticatedAPIRootView, NautobotAPIVersionMixin
from nautobot.core.forms import TableConfigForm
from nautobot.core.views.generic import GenericView
from nautobot.core.views.mixins import AdminRequiredMixin
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.extras.plugins.tables import InstalledPluginsTable


class InstalledPluginsView(AdminRequiredMixin, View):
    """
    View for listing all installed plugins.
    """

    table = InstalledPluginsTable

    def get(self, request):
        data = []
        for plugin in apps.get_app_configs():
            if plugin.name in settings.PLUGINS:
                data.append(
                    {
                        "name": plugin.verbose_name,
                        "package_name": plugin.name,
                        "app_label": plugin.label,
                        "author": plugin.author,
                        "author_email": plugin.author_email,
                        "description": plugin.description,
                        "version": plugin.version,
                        "actions": {
                            "home": plugin.home_view_name,
                            "configure": plugin.config_view_name,
                            "docs": plugin.docs_view_name,
                        },
                    }
                )
        table = self.table(data, user=request.user)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(table)

        return render(
            request,
            "extras/plugins_list.html",
            {
                "table": table,
                "table_config_form": TableConfigForm(table=table),
                "filter_form": None,
            },
        )


class InstalledPluginDetailView(GenericView):
    """
    View for showing details of an installed plugin.
    """

    def get(self, request, plugin):
        plugin_config = apps.get_app_config(plugin)
        if plugin_config.name not in settings.PLUGINS:
            raise Http404

        return render(
            request,
            "extras/plugin_detail.html",
            {
                "object": plugin_config,
            },
        )


class InstalledPluginsAPIView(NautobotAPIVersionMixin, APIView):
    """
    API view for listing all installed non-core Apps.
    """

    permission_classes = [permissions.IsAdminUser]

    def get_view_name(self):
        return "Installed Plugins"

    @staticmethod
    def _get_plugin_data(plugin_app_config):
        try:
            home_url = reverse(plugin_app_config.home_view_name)
        except NoReverseMatch:
            home_url = None
        try:
            config_url = reverse(plugin_app_config.config_view_name)
        except NoReverseMatch:
            config_url = None
        try:
            docs_url = reverse(plugin_app_config.docs_view_name)
        except NoReverseMatch:
            docs_url = None
        return {
            "name": plugin_app_config.verbose_name,
            "package": plugin_app_config.name,
            "author": plugin_app_config.author,
            "author_email": plugin_app_config.author_email,
            "description": plugin_app_config.description,
            "version": plugin_app_config.version,
            "home_url": home_url,
            "config_url": config_url,
            "docs_url": docs_url,
        }

    @extend_schema(exclude=True)
    def get(self, request, format=None):  # pylint: disable=redefined-builtin
        return Response([self._get_plugin_data(apps.get_app_config(plugin)) for plugin in settings.PLUGINS])


class PluginsAPIRootView(AuthenticatedAPIRootView):
    name = "Apps"
    description = "API extension point for installed Nautobot Apps"

    @staticmethod
    def _get_plugin_entry(plugin, app_config, request, format_):
        # Check if the plugin specifies any API URLs
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
            # The plugin does not include an api-root url
            entry = None

        return entry

    @extend_schema(exclude=True)
    def get(self, request, format=None):  # pylint: disable=redefined-builtin
        entries = []
        for plugin in settings.PLUGINS:
            app_config = apps.get_app_config(plugin)
            entry = self._get_plugin_entry(plugin, app_config, request, format)
            if entry is not None:
                entries.append(entry)

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
