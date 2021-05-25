import platform
import sys

from django.conf import settings
from django.db.models import F
from django.http import HttpResponseServerError
from django.shortcuts import render
from django.template import loader
from django.template.exceptions import TemplateDoesNotExist
from django.urls import reverse
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_500_TEMPLATE_NAME
from django.views.generic import TemplateView, View
from packaging import version
from graphene_django.views import GraphQLView

from nautobot.circuits.models import Circuit, Provider
from nautobot.dcim.models import (
    Cable,
    ConsolePort,
    Device,
    DeviceType,
    Interface,
    PowerPanel,
    PowerFeed,
    PowerPort,
    Rack,
    Site,
    VirtualChassis,
)
from nautobot.core.constants import SEARCH_MAX_RESULTS, SEARCH_TYPES
from nautobot.core.forms import SearchForm
from nautobot.core.releases import get_latest_release
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.models import GitRepository, GraphQLQuery, ObjectChange, JobResult
from nautobot.extras.forms import GraphQLQueryForm
from nautobot.ipam.models import Aggregate, IPAddress, Prefix, VLAN, VRF
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster, VirtualMachine


class HomeView(TemplateView):
    template_name = "home.html"

    def get(self, request):

        connected_consoleports = (
            ConsolePort.objects.restrict(request.user, "view")
            .prefetch_related("_path")
            .filter(_path__destination_id__isnull=False)
        )
        connected_powerports = (
            PowerPort.objects.restrict(request.user, "view")
            .prefetch_related("_path")
            .filter(_path__destination_id__isnull=False)
        )
        connected_interfaces = (
            Interface.objects.restrict(request.user, "view")
            .prefetch_related("_path")
            .filter(_path__destination_id__isnull=False, pk__lt=F("_path__destination_id"))
        )

        # Job history
        # Only get JobResults that have reached a terminal state
        job_results = (
            JobResult.objects.filter(status__in=JobResultStatusChoices.TERMINAL_STATE_CHOICES)
            .defer("data")
            .order_by("-completed")
        )

        stats = {
            # Organization
            "site_count": Site.objects.restrict(request.user, "view").count(),
            "tenant_count": Tenant.objects.restrict(request.user, "view").count(),
            # DCIM
            "rack_count": Rack.objects.restrict(request.user, "view").count(),
            "devicetype_count": DeviceType.objects.restrict(request.user, "view").count(),
            "device_count": Device.objects.restrict(request.user, "view").count(),
            "interface_connections_count": connected_interfaces.count(),
            "cable_count": Cable.objects.restrict(request.user, "view").count(),
            "console_connections_count": connected_consoleports.count(),
            "power_connections_count": connected_powerports.count(),
            "powerpanel_count": PowerPanel.objects.restrict(request.user, "view").count(),
            "powerfeed_count": PowerFeed.objects.restrict(request.user, "view").count(),
            "virtualchassis_count": VirtualChassis.objects.restrict(request.user, "view").count(),
            # IPAM
            "vrf_count": VRF.objects.restrict(request.user, "view").count(),
            "aggregate_count": Aggregate.objects.restrict(request.user, "view").count(),
            "prefix_count": Prefix.objects.restrict(request.user, "view").count(),
            "ipaddress_count": IPAddress.objects.restrict(request.user, "view").count(),
            "vlan_count": VLAN.objects.restrict(request.user, "view").count(),
            # Circuits
            "provider_count": Provider.objects.restrict(request.user, "view").count(),
            "circuit_count": Circuit.objects.restrict(request.user, "view").count(),
            # Virtualization
            "cluster_count": Cluster.objects.restrict(request.user, "view").count(),
            "virtualmachine_count": VirtualMachine.objects.restrict(request.user, "view").count(),
            # Extras
            "gitrepository_count": GitRepository.objects.restrict(request.user, "view").count(),
        }

        changelog = ObjectChange.objects.restrict(request.user, "view").prefetch_related("user", "changed_object_type")

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
                "stats": stats,
                "job_results": job_results[:10],
                "changelog": changelog[:15],
                "new_release": new_release,
            }
        )

        return self.render_to_response(context)


class SearchView(View):
    def get(self, request):

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

            if form.cleaned_data["obj_type"]:
                # Searching for a single type of object
                obj_types = [form.cleaned_data["obj_type"]]
            else:
                # Searching all object types
                obj_types = SEARCH_TYPES.keys()

            for obj_type in obj_types:

                queryset = SEARCH_TYPES[obj_type]["queryset"].restrict(request.user, "view")
                filterset = SEARCH_TYPES[obj_type]["filterset"]
                table = SEARCH_TYPES[obj_type]["table"]
                url = SEARCH_TYPES[obj_type]["url"]

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


@requires_csrf_token
def server_error(request, template_name=ERROR_500_TEMPLATE_NAME):
    """
    Custom 500 handler to provide additional context when rendering 500.html.
    """
    try:
        template = loader.get_template(template_name)
    except TemplateDoesNotExist:
        return HttpResponseServerError("<h1>Server Error (500)</h1>", content_type="text/html")
    type_, error, traceback = sys.exc_info()

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


class CustomGraphQLView(GraphQLView):
    def render_graphiql(self, request, **data):
        query_slug = request.GET.get("slug")
        if query_slug:
            data["obj"] = GraphQLQuery.objects.get(slug=query_slug)
            data["editing"] = True
        data["graphiql"] = True
        data["saved_graphiql_queries"] = GraphQLQuery.objects.all()
        data["form"] = GraphQLQueryForm
        return render(request, self.graphiql_template, data)
