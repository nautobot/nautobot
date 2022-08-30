from collections import OrderedDict

from django.apps import apps
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import render
from django.urls.exceptions import NoReverseMatch
from django.views.generic import View
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from django_tables2 import RequestConfig

from nautobot.core.api.views import NautobotAPIVersionMixin
from nautobot.utilities.forms import TableConfigForm
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.extras.plugins.tables import InstalledPluginsTable
from nautobot.utilities.views import AdminRequiredMixin


class InstalledPluginsView(AdminRequiredMixin, View):
    """
    View for listing all installed plugins.
    """

    table = InstalledPluginsTable

    def get(self, request):
        plugins = [apps.get_app_config(plugin) for plugin in settings.PLUGINS]
        data = []
        for plugin in plugins:
            data.append(
                {
                    "name": plugin.verbose_name,
                    "package_name": plugin.name,
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


class InstalledPluginDetailView(LoginRequiredMixin, View):
    """
    View for showing details of an installed plugin.
    """

    def get(self, request, plugin):
        if plugin not in settings.PLUGINS:
            raise Http404

        plugin_config = apps.get_app_config(plugin)
        return render(
            request,
            "extras/plugin_detail.html",
            {
                "object": plugin_config,
            },
        )


class InstalledPluginsAPIView(NautobotAPIVersionMixin, APIView):
    """
    API view for listing all installed plugins
    """

    permission_classes = [permissions.IsAdminUser]
    _ignore_model_permissions = True

    def get_view_name(self):
        return "Installed Plugins"

    @staticmethod
    def _get_plugin_data(plugin_app_config):
        return {
            "name": plugin_app_config.verbose_name,
            "package": plugin_app_config.name,
            "author": plugin_app_config.author,
            "author_email": plugin_app_config.author_email,
            "description": plugin_app_config.description,
            # TODO: Remove verison key/value when bumping to major revision
            "verison": plugin_app_config.version,
            "version": plugin_app_config.version,
        }

    @extend_schema(exclude=True)
    def get(self, request, format=None):  # pylint: disable=redefined-builtin
        return Response([self._get_plugin_data(apps.get_app_config(plugin)) for plugin in settings.PLUGINS])


class PluginsAPIRootView(NautobotAPIVersionMixin, APIView):
    _ignore_model_permissions = True

    def get_view_name(self):
        return "Plugins"

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
