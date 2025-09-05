import contextlib
import datetime
import logging
import os
import platform
import posixpath
import re
import sys
import time

from db_file_storage.views import get_file
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseForbidden, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template import loader, RequestContext, Template
from django.template.exceptions import TemplateDoesNotExist
from django.urls import NoReverseMatch, resolve, reverse
from django.utils.encoding import smart_str
from django.views.csrf import csrf_failure as _csrf_failure
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_500_TEMPLATE_NAME, page_not_found
from django.views.generic import TemplateView, View
from django.views.static import serve
from graphene_django.views import GraphQLView
from packaging import version
from prometheus_client import (
    CollectorRegistry,
    CONTENT_TYPE_LATEST,
    generate_latest,
    multiprocess,
    REGISTRY,
)
from prometheus_client.metrics_core import GaugeMetricFamily
from prometheus_client.registry import Collector
import redis.exceptions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response
from rest_framework.versioning import AcceptHeaderVersioning
from rest_framework.views import APIView

from nautobot.core.celery import app
from nautobot.core.constants import SEARCH_MAX_RESULTS
from nautobot.core.forms import SearchForm
from nautobot.core.releases import get_latest_release
from nautobot.core.utils.config import get_settings_or_config
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.core.utils.permissions import get_permission_for_model
from nautobot.extras.forms import GraphQLQueryForm
from nautobot.extras.models import FileProxy, GraphQLQuery, Status
from nautobot.extras.registry import registry

logger = logging.getLogger(__name__)


class HomeView(AccessMixin, TemplateView):
    template_name = "home.html"

    def render_additional_content(self, request, context, details):
        # Collect all custom data using callback functions.
        for key, data in details.get("custom_data", {}).items():
            if callable(data):
                context[key] = data(request)
            else:
                context[key] = data

        # Create standalone template
        path = f"{details['template_path']}{details['custom_template']}"
        if os.path.isfile(path):
            with open(path, "r") as f:
                html = f.read()
        else:
            raise TemplateDoesNotExist(path)

        template = Template(html)

        additional_context = RequestContext(request, context)
        return template.render(additional_context)

    def get(self, request, *args, **kwargs):
        # Redirect user to login page if not authenticated
        if not request.user.is_authenticated:
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


class MediaView(AccessMixin, View):
    """
    Serves media files while enforcing login restrictions.

    This view wraps Django's `serve()` function to ensure that access to media files (with the exception of
    branding files defined in `settings.BRANDING_FILEPATHS`) is restricted to authenticated users.
    """

    def get(self, request, path):
        if request.user.is_authenticated:
            return serve(request, path, document_root=settings.MEDIA_ROOT)

        # Unauthenticated users can access BRANDING_FILEPATHS only
        if posixpath.normpath(path).lstrip("/") in settings.BRANDING_FILEPATHS.values():
            return serve(request, path, document_root=settings.MEDIA_ROOT)

        return self.handle_no_permission()


class WorkerStatusView(UserPassesTestMixin, TemplateView):
    template_name = "utilities/worker_status.html"

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        from nautobot.extras.models import JobResult
        from nautobot.extras.tables import JobResultTable

        # Sort queues but move the default queue to the front so that it appears first
        def sort_queues(queue):
            return (queue != settings.CELERY_TASK_DEFAULT_QUEUE, queue)  # False sorts before true in Python sorted

        # Sort workers on hostname first, then worker name -- celery worker names are in the form name@hostname (celery@worker.example.com)
        def sort_workers(worker):
            return list(reversed(worker.split("@")))

        # Use a long timeout to retrieve the initial list of workers
        max_timeout = 60
        timeout = request.GET.get("timeout", "5")
        if not timeout.isdigit():
            timeout = 5
        elif int(timeout) > max_timeout:
            timeout = max_timeout
        else:
            timeout = int(timeout)

        celery_inspect = app.control.inspect(timeout=timeout)

        try:
            # stats() returns a dict of {worker_name: stats_dict}
            worker_stats = celery_inspect.stats()
        except redis.exceptions.ConnectionError:
            # Celery seems to be not smart enough to auto-retry on intermittent failures, so let's do it ourselves:
            try:
                worker_stats = celery_inspect.stats()
            except redis.exceptions.ConnectionError as err:
                logger.error("Repeated ConnectionError from Celery/Redis: %s", err)
                worker_stats = None

        active_tasks = reserved_tasks = active_queues = {}
        if worker_stats:
            # Set explicit list of workers to speed up subsequent queries
            celery_inspect = app.control.inspect(list(worker_stats.keys()), timeout=5.0)

            with contextlib.suppress(redis.exceptions.ConnectionError):
                # active() returns a dict of {worker_name: [task_dict, task_dict, ...]}
                active_tasks = celery_inspect.active() or {}

                # reserved() returns a dict of {worker_name: [task_dict, task_dict, ...]}
                reserved_tasks = celery_inspect.reserved() or {}

                # active_queues() returns a dict of {worker_name: [queue_dict, queue_dict, ...]}
                active_queues = celery_inspect.active_queues() or {}
        else:
            # No workers were found
            worker_stats = {}

        workers = []
        for worker_name in sorted(worker_stats, key=sort_workers):
            worker_details = worker_stats[worker_name]
            active_task_job_results = JobResult.objects.filter(
                id__in=[task["id"] for task in active_tasks.get(worker_name, [])]
            ).only("name", "date_created")
            reserved_task_job_results = JobResult.objects.filter(
                id__in=[task["id"] for task in reserved_tasks.get(worker_name, [])]
            ).only("name", "date_created")
            running_tasks_table = JobResultTable(
                active_task_job_results, exclude=["actions", "job_model", "summary", "user", "status"]
            )
            pending_tasks_table = JobResultTable(
                reserved_task_job_results, exclude=["actions", "job_model", "summary", "user", "status"]
            )

            # Sort the worker's queue list
            queues = sorted([queue["name"] for queue in active_queues.get(worker_name, [])], key=sort_queues)

            workers.append(
                {
                    "hostname": worker_name,
                    "running_tasks_table": running_tasks_table,
                    "pending_tasks_table": pending_tasks_table,
                    "queues": queues,
                    "uptime": worker_details["uptime"],
                }
            )

        # Count the number of workers per queue
        queue_worker_count = {
            settings.CELERY_TASK_DEFAULT_QUEUE: set(),
        }
        for worker_name, task_queue_list in active_queues.items():
            distinct_queues = {q["name"] for q in task_queue_list}
            for queue in distinct_queues:
                queue_worker_count.setdefault(queue, set())
                queue_worker_count[queue].add(worker_name)

        # Sort the queue_worker_count dictionary by queue name, then by worker hostname/name
        # Then make the default queue the first entry
        queue_worker_count = {
            queue_name: sorted(queue_worker_count[queue_name], key=sort_workers)
            for queue_name in sorted(queue_worker_count, key=sort_queues)
        }

        context = {
            "worker_status": {
                "max_timeout": max_timeout,
                "queue_worker_count": queue_worker_count,
                "timeout": timeout,
                "workers": workers,
            },
        }

        return self.render_to_response(context)


class ThemePreviewView(LoginRequiredMixin, TemplateView):
    template_name = "utilities/theme_preview.html"

    def get_context_data(self, **kwargs):
        return {
            "content_type": ContentType.objects.get_for_model(Status),
            "object": Status.objects.first(),
            "verbose_name": Status.objects.all().model._meta.verbose_name,
            "verbose_name_plural": Status.objects.all().model._meta.verbose_name_plural,
        }


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
                try:
                    view_func = resolve(reverse(url)).func
                    # For UIViewSet, view_func.cls gets what we need; for an ObjectListView, view_func.view_class is it.
                    view_or_viewset = getattr(view_func, "cls", getattr(view_func, "view_class", None))
                    queryset = view_or_viewset.queryset.restrict(request.user, "view")
                    # For a UIViewSet, .filterset_class, for an ObjectListView, .filterset.
                    filterset = getattr(view_or_viewset, "filterset_class", getattr(view_or_viewset, "filterset", None))
                    # For a UIViewSet, .table_class, for an ObjectListView, .table.
                    table = getattr(view_or_viewset, "table_class", getattr(view_or_viewset, "table", None))

                    # Construct the results table for this object type
                    filtered_queryset = filterset({"q": form.cleaned_data["q"]}, queryset=queryset).qs
                    table = table(filtered_queryset, hide_hierarchy_ui=True, orderable=False)
                    table.paginate(per_page=SEARCH_MAX_RESULTS)

                    if table.page:
                        results.append(
                            {
                                "name": queryset.model._meta.verbose_name_plural,
                                "table": table,
                                "url": f"{reverse(url)}?q={form.cleaned_data.get('q')}",
                            }
                        )
                except NoReverseMatch:
                    messages.error(request, f'Missing URL "{url}" - unable to show search results for {modelname}.')

        return render(
            request,
            "search.html",
            {
                "form": form,
                "results": results,
            },
        )


class StaticMediaFailureView(View):  # NOT using LoginRequiredMixin here as this may happen even on the login page
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
    context = {
        "error": error,
        "exception": str(type_),
        "nautobot_version": settings.VERSION,
        "python_version": platform.python_version(),
    }

    return HttpResponseServerError(template.render(context, request))


def csrf_failure(request, reason="", template_name="403_csrf_failure.html"):
    """Custom 403 CSRF failure handler to account for additional context.

    If Nautobot is set to DEBUG the default view for csrf_failure.
    `403_csrf_failure.html` template name is used over `403_csrf.html` to account for
    additional context that is required to render the inherited templates.
    """
    if settings.DEBUG:
        return _csrf_failure(request, reason=reason)
    t = loader.get_template(template_name)
    context = {
        "reason": reason,
        "settings": settings,
        "nautobot_version": settings.VERSION,
        "python_version": platform.python_version(),
    }
    return HttpResponseForbidden(t.render(context), content_type="text/html")


class CustomGraphQLView(LoginRequiredMixin, GraphQLView):
    def render_graphiql(self, request, **data):
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


class PrometheusVersioning(AcceptHeaderVersioning):
    """Overwrite the Nautobot API Version with the prometheus API version. Otherwise Telegraf/Prometheus won't be able to poll due to a version mismatch."""

    default_version = re.findall("version=(.+);", CONTENT_TYPE_LATEST)[0]


class PlainTextRenderer(BaseRenderer):
    """Render API as plain text instead of JSON."""

    media_type = "text/plain"
    format = "txt"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """Render the data."""
        return smart_str(data, encoding=self.charset)


class NautobotMetricsView(APIView):
    renderer_classes = [PlainTextRenderer]
    versioning_class = PrometheusVersioning
    permission_classes = [AllowAny]
    serializer_class = None

    def get(self, request):
        """Exports /metrics.
        This overwrites the default django_prometheus view to inject metrics from Nautobot apps.
        Note that we cannot use `prometheus_django.ExportToDjangoView`, as that is a simple function, and we need access to
        the `prometheus_registry` variable that is defined inside of it."""
        if "PROMETHEUS_MULTIPROC_DIR" in os.environ or "prometheus_multiproc_dir" in os.environ:
            prometheus_registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(prometheus_registry)
        else:
            prometheus_registry = REGISTRY
        # Instantiate and register the collector. Note that this has to be done every time this view is accessed, because
        # the registry for multiprocess metrics is also instantiated every time this view is accessed. As a result, the
        # same goes for the registration of the collector to the registry.
        try:
            nb_app_collector = NautobotAppMetricsCollector()
            prometheus_registry.register(nb_app_collector)
        except ValueError:
            # Collector already registered, we are running without multiprocessing
            pass
        metrics_page = generate_latest(prometheus_registry)
        return Response(metrics_page, content_type=CONTENT_TYPE_LATEST)


class NautobotMetricsViewAuth(NautobotMetricsView):
    permission_classes = [IsAuthenticated]


@permission_required(get_permission_for_model(FileProxy, "view"), raise_exception=True)
def get_file_with_authorization(request, *args, **kwargs):
    """Patch db_file_storage view with authentication."""
    # Make sure user has permissions
    queryset = FileProxy.objects.restrict(request.user, "view")
    get_object_or_404(queryset, file=request.GET.get("name"))

    return get_file(request, *args, **kwargs)


class AboutView(AccessMixin, TemplateView):
    """
    Nautobot About View which displays general information about Nautobot and contact details
    for Network to Code.
    """

    template_name = "about.html"

    def get(self, request, *args, **kwargs):
        # Redirect user to login page if not authenticated
        if not request.user.is_authenticated:
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

        # Support contract state
        support_expiration_date = get_settings_or_config("NTC_SUPPORT_CONTRACT_EXPIRATION_DATE")
        support_contract_active = support_expiration_date and support_expiration_date >= datetime.date.today()

        context = self.get_context_data()
        context.update(
            {
                "new_release": new_release,
                "support_contract_active": support_contract_active,
                "support_expiration_date": support_expiration_date,
            }
        )

        return self.render_to_response(context)


class RenderJinjaView(LoginRequiredMixin, TemplateView):
    """Render a Jinja template with context data."""

    template_name = "utilities/render_jinja2.html"
