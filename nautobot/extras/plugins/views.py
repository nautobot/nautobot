from collections import OrderedDict

from django.apps import apps
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
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

from nautobot.core.api.views import NautobotAPIVersionMixin
from nautobot.core.forms import TableConfigForm
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.extras.plugins.tables import InstalledAppsTable


class InstalledAppsView(LoginRequiredMixin, View):
    """
    View for listing all installed Apps.
    """

    table = InstalledAppsTable

    def get(self, request):
        data = []
        for app in apps.get_app_configs():
            if app.name in settings.PLUGINS:
                data.append(
                    {
                        "name": app.verbose_name,
                        "package_name": app.name,
                        "app_label": app.label,
                        "author": app.author,
                        "author_email": app.author_email,
                        "description": app.description,
                        "version": app.version,
                        "actions": {
                            "home": app.home_view_name,
                            "configure": app.config_view_name,
                            "docs": app.docs_view_name,
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


class InstalledAppDetailView(LoginRequiredMixin, View):
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
            },
        )


class InstalledAppsAPIView(NautobotAPIVersionMixin, APIView):
    """
    API view for listing all installed non-core Apps.
    """

    permission_classes = [permissions.IsAdminUser]
    _ignore_model_permissions = True

    def get_view_name(self):
        return "Installed Apps"

    @staticmethod
    def _get_app_data(app_config):
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
            "description": app_config.description,
            "version": app_config.version,
            "home_url": home_url,
            "config_url": config_url,
            "docs_url": docs_url,
        }

    @extend_schema(exclude=True)
    def get(self, request, format=None):  # pylint: disable=redefined-builtin
        return Response([self._get_app_data(apps.get_app_config(app)) for app in settings.PLUGINS])


class AppsAPIRootView(NautobotAPIVersionMixin, APIView):
    _ignore_model_permissions = True

    def get_view_name(self):
        return "Apps"

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
