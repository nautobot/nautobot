import os
import platform
import sys

from django.conf import settings
from django.contrib.auth.mixins import AccessMixin
from django.http import HttpResponseServerError, JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.template import loader, RequestContext, Template
from django.template.exceptions import TemplateDoesNotExist
from django.urls import reverse
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_500_TEMPLATE_NAME, page_not_found
from django.views.csrf import csrf_failure as _csrf_failure
from django.views.generic import TemplateView, View
from packaging import version
from graphene_django.views import GraphQLView

from nautobot.core.constants import SEARCH_MAX_RESULTS, SEARCH_TYPES
from nautobot.core.forms import SearchForm
from nautobot.core.releases import get_latest_release
from nautobot.extras.models import GraphQLQuery
from nautobot.extras.registry import registry
from nautobot.extras.forms import GraphQLQueryForm
from nautobot.utilities.config import get_settings_or_config


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
        query_slug = request.GET.get("slug")
        if query_slug:
            data["obj"] = GraphQLQuery.objects.get(slug=query_slug)
            data["editing"] = True
        data["saved_graphiql_queries"] = GraphQLQuery.objects.all()
        data["form"] = GraphQLQueryForm
        return render(request, self.graphiql_template, data)
