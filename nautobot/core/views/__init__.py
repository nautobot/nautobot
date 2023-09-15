import os
import platform
import sys
import time

from django.apps import apps
import prometheus_client
from django.conf import settings
from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponseServerError, JsonResponse, HttpResponseForbidden, HttpResponse
from django.shortcuts import redirect, render
from django.template import loader, RequestContext, Template
from django.template.exceptions import TemplateDoesNotExist
from django.urls import resolve, reverse
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_500_TEMPLATE_NAME, page_not_found
from django.views.csrf import csrf_failure as _csrf_failure
from django.views.generic import TemplateView, View
from packaging import version
from graphene_django.views import GraphQLView
from prometheus_client import multiprocess
from prometheus_client.metrics_core import GaugeMetricFamily
from prometheus_client.registry import Collector

from nautobot.core.constants import SEARCH_MAX_RESULTS
from nautobot.core.forms import SearchForm
from nautobot.core.releases import get_latest_release
from nautobot.core.utils.config import get_settings_or_config
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.extras.models import GraphQLQuery
from nautobot.extras.registry import registry
from nautobot.extras.forms import GraphQLQueryForm


class HomeView(AccessMixin, TemplateView):
    template_name = "home.html"
    use_new_ui = True

    def render_additional_content(self, request, context, details):
        # Collect all custom data using callback functions.
        for key, data in details.get("custom_data", {}).items():
            if callable(data):
                context[key] = data(request)
            else:
                context[key] = data

        # Create standalone template
        path = f'{details["template_path"]}{details["custom_template"]}'
        if os.path.isfile(path):
            with open(path, "r") as f:
                html = f.read()
        else:
            raise TemplateDoesNotExist(path)

        template = Template(html)

        additional_context = RequestContext(request, context)
        return template.render(additional_context)

    def get(self, request, *args, **kwargs):
        # Redirect user to login page if not authenticated and HIDE_RESTRICTED_UI is set to True
        if not request.user.is_authenticated and get_settings_or_config("HIDE_RESTRICTED_UI"):
            return self.handle_no_permission()
        # Check whether a new release is available. (Only for staff/superusers.)
        new_release = None
        if request.user.is_staff or request.user.is_superuser:
            latest_release, release_url = get_latest_release()
            if isinstance(latest_release, version.Version):
                current_version = version.parse(settings.VERSION)
                if latest_release > current_version:
                    new_release = {
                        "version": str(latest_release),
                        "url": release_url,
                    }

        context = self.get_context_data()
        context.update(
            {
                "search_form": SearchForm(),
                "new_release": new_release,
            }
        )

        # Loop over homepage layout to collect all additional data and create custom panels.
        for panel_details in registry["homepage_layout"]["panels"].values():
            if panel_details.get("custom_template"):
                panel_details["rendered_html"] = self.render_additional_content(request, context, panel_details)

            else:
                for item_details in panel_details["items"].values():
                    if item_details.get("custom_template"):
                        item_details["rendered_html"] = self.render_additional_content(request, context, item_details)

                    elif item_details.get("model"):
                        # If there is a model attached collect object count.
                        item_details["count"] = item_details["model"].objects.restrict(request.user, "view").count()

                    elif item_details.get("items"):
                        # Collect count for grouped objects.
                        for group_item_details in item_details["items"].values():
                            if group_item_details.get("custom_template"):
                                group_item_details["rendered_html"] = self.render_additional_content(
                                    request, context, group_item_details
                                )
                            elif group_item_details.get("model"):
                                group_item_details["count"] = (
                                    group_item_details["model"].objects.restrict(request.user, "view").count()
                                )

        return self.render_to_response(context)


class SearchView(AccessMixin, View):
    def get(self, request):
        # if user is not authenticated, redirect to login page
        # when attempting to search
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # No query
        if "q" not in request.GET:
            return render(
                request,
                "search.html",
                {
                    "form": SearchForm(),
                },
            )

        form = SearchForm(request.GET)
        results = []

        if form.is_valid():
            # Build the list of (app_label, modelname) tuples, representing all models included in the global search,
            # based on the `app_config.searchable_models` list (if any) defined by each app
            searchable_models = []
            for app_config in apps.get_app_configs():
                if hasattr(app_config, "searchable_models"):
                    searchable_models += [(app_config.label, modelname) for modelname in app_config.searchable_models]

            if form.cleaned_data["obj_type"]:
                # Searching for a single type of object
                obj_types = [form.cleaned_data["obj_type"]]
            else:
                # Searching all object types
                obj_types = [model_info[1] for model_info in searchable_models]

            for label, modelname in searchable_models:
                if modelname not in obj_types:
                    continue
                # Based on the label and modelname, reverse-lookup the list URL, then the view or UIViewSet
                # corresponding to that URL, and finally the queryset, filterset, and table classes needed
                # to find and display the model search results.
                url = get_route_for_model(f"{label}.{modelname}", "list")
                view_func = resolve(reverse(url)).func
                # For a UIViewSet, view_func.cls gets what we need; for an ObjectListView, view_func.view_class is it.
                view_or_viewset = getattr(view_func, "cls", getattr(view_func, "view_class", None))
                queryset = view_or_viewset.queryset.restrict(request.user, "view")
                # For a UIViewSet, .filterset_class, for an ObjectListView, .filterset.
                filterset = getattr(view_or_viewset, "filterset_class", getattr(view_or_viewset, "filterset", None))
                # For a UIViewSet, .table_class, for an ObjectListView, .table.
                table = getattr(view_or_viewset, "table_class", getattr(view_or_viewset, "table", None))

                # Construct the results table for this object type
                filtered_queryset = filterset({"q": form.cleaned_data["q"]}, queryset=queryset).qs
                table = table(filtered_queryset, orderable=False)
                table.paginate(per_page=SEARCH_MAX_RESULTS)

                if table.page:
                    results.append(
                        {
                            "name": queryset.model._meta.verbose_name_plural,
                            "table": table,
                            "url": f"{reverse(url)}?q={form.cleaned_data.get('q')}",
                        }
                    )

        return render(
            request,
            "search.html",
            {
                "form": form,
                "results": results,
            },
        )


class StaticMediaFailureView(View):
    """
    Display a user-friendly error message with troubleshooting tips when a static media file fails to load.
    """

    def get(self, request):
        return render(request, "media_failure.html", {"filename": request.GET.get("filename")})


def resource_not_found(request, exception):
    if request.path.startswith("/api/"):
        return JsonResponse({"detail": "Not found."}, status=404)
    else:
        return page_not_found(request, exception, "404.html")


@requires_csrf_token
def server_error(request, template_name=ERROR_500_TEMPLATE_NAME):
    """
    Custom 500 handler to provide additional context when rendering 500.html.
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        return HttpResponseServerError("<h1>Server Error (500)</h1>", content_type="text/html")
    type_, error, _traceback = sys.exc_info()

    return HttpResponseServerError(
        template.render(
            {
                "error": error,
                "exception": str(type_),
                "nautobot_version": settings.VERSION,
                "python_version": platform.python_version(),
            }
        )
    )


def csrf_failure(request, reason="", template_name="403_csrf_failure.html"):
    """Custom 403 CSRF failure handler to account for additional context.

    If Nautobot is set to DEBUG the default view for csrf_failure.
    `403_csrf_failure.html` template name is used over `403_csrf.html` to account for
    additional context that is required to render the inherited templates.
    """
    if settings.DEBUG:
        return _csrf_failure(request, reason=reason)
    t = loader.get_template(template_name)
    context = {"settings": settings, "reason": reason}
    return HttpResponseForbidden(t.render(context), content_type="text/html")


class CustomGraphQLView(GraphQLView):
    def render_graphiql(self, request, **data):
        if not request.user.is_authenticated and get_settings_or_config("HIDE_RESTRICTED_UI"):
            graphql_url = reverse("graphql")
            login_url = reverse(settings.LOGIN_URL)
            return redirect(f"{login_url}?next={graphql_url}")
        query_name = request.GET.get("name")
        if query_name:
            data["obj"] = GraphQLQuery.objects.get(name=query_name)
            data["editing"] = True
        data["saved_graphiql_queries"] = GraphQLQuery.objects.all()
        data["form"] = GraphQLQueryForm
        return render(request, self.graphiql_template, data)


class NautobotAppMetricsCollector(Collector):
    """Custom Nautobot metrics collector.

    Metric collector that reads from registry["plugin_metrics"] and yields any metrics registered there."""

    def collect(self):
        """Collect metrics from plugins."""
        start = time.time()
        for metric_generator in registry["app_metrics"]:
            yield from metric_generator()
        gauge = GaugeMetricFamily("nautobot_app_metrics_processing_ms", "Time in ms to generate the app metrics")
        duration = time.time() - start
        gauge.add_metric([], format(duration * 1000, ".5f"))
        yield gauge


def nautobot_metrics_view(request):
    """Exports /metrics.

    This overwrites the default django_prometheus view to inject metrics from Nautobot apps.

    Note that we cannot use `prometheus_django.ExportToDjangoView`, as that is a simple function, and we need access to
    the `prometheus_registry` variable that is defined inside of it."""
    if "PROMETHEUS_MULTIPROC_DIR" in os.environ or "prometheus_multiproc_dir" in os.environ:
        prometheus_registry = prometheus_client.CollectorRegistry()
        multiprocess.MultiProcessCollector(prometheus_registry)
    else:
        prometheus_registry = prometheus_client.REGISTRY
    # Instantiate and register the collector. Note that this has to be done every time this view is accessed, because
    # the registry for multiprocess metrics is also instantiated every time this view is accessed. As a result, the
    # same goes for the registration of the collector to the registry.
    try:
        nb_app_collector = NautobotAppMetricsCollector()
        prometheus_registry.register(nb_app_collector)
    except ValueError:
        # Collector already registered, we are running without multiprocessing
        pass
    metrics_page = prometheus_client.generate_latest(prometheus_registry)
    return HttpResponse(metrics_page, content_type=prometheus_client.CONTENT_TYPE_LATEST)
