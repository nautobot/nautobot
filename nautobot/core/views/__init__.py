import json
import os
import platform
import re
import sys

from django.conf import settings
from django.contrib.auth.mixins import AccessMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseServerError, JsonResponse
from django.shortcuts import render
from django.template import loader, RequestContext, Template
from django.template.exceptions import TemplateDoesNotExist
from django.urls import reverse
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_500_TEMPLATE_NAME, page_not_found
from django.views.generic import TemplateView, View
from django_filters import filters, ModelMultipleChoiceFilter
from packaging import version
from graphene_django.views import GraphQLView

from nautobot.core.constants import SEARCH_MAX_RESULTS, SEARCH_TYPES
from nautobot.core.forms import SearchForm
from nautobot.core.releases import get_latest_release
from nautobot.extras.filters import StatusFilter
from nautobot.extras.models import GraphQLQuery, Status, Tag
from nautobot.extras.registry import registry
from nautobot.extras.forms import GraphQLQueryForm
from nautobot.utilities.config import get_settings_or_config
from nautobot.utilities.filters import RelatedMembershipBooleanFilter
from nautobot.utilities.forms import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.utilities.utils import get_filterset_for_model, get_model_api_endpoint


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

    def get(self, request):
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
        data["saved_graphiql_queries"] = GraphQLQuery.objects.all()
        data["form"] = GraphQLQueryForm
        return render(request, self.graphiql_template, data)


class LookupFieldsChoicesView(View):
    queryset = None

    @staticmethod
    def __build_lookup_label(field_name, verbose_name):
        """
        Return lookup expr with its verbose name

        Args:
            field_name (str): Field name e.g slug__iew
            verbose_name (str): The verbose name for the lookup exper which is suffixed to the field name e.g iew -> iendswith

        Examples:
            >>> __build_lookup_label("slug__iew", "iendswith")
            >>> "iendswith(iew)"
        """
        label = ""
        search = re.search("__.+$", field_name)
        if search is not None:
            text = search.group().replace("__", "")
            label = f"({text})"

        return verbose_name + label

    def __get_field_lookup_exper(self, filterset, field_name):
        """
        Return all lookup expressions for `field_name` in the `filterset`
        """
        if field_name.startswith("has_"):
            return [{"id": field_name, "name": "exact"}]

        lookup_expr = [
            {
                "id": name,
                "name": self.__build_lookup_label(name, field.lookup_expr),
            }
            for name, field in filterset.items()
            if name.startswith(field_name) and not name.startswith("has_")
        ]
        return lookup_expr or [{"id": "exact", "name": "exact - Not Found"}]

    def get(self, request):
        contenttype = request.GET.get("contenttype")
        field_name = request.GET.get("field_name")
        try:
            app_label, model_name = contenttype.split(".")
            contenttype = ContentType.objects.get(app_label=app_label, model=model_name)
            filterset = get_filterset_for_model(contenttype.model_class())
            if filterset is not None:
                lookup_exper = self.__get_field_lookup_exper(filterset.base_filters, field_name)
            # TODO Timizuo Raise Error if filterset not found
        except ContentType.DoesNotExist:
            lookup_exper = []

        return JsonResponse({
            "count": len(lookup_exper),
            "next": None,
            "previous": None,
            "results": lookup_exper
        })


class LookupFieldTypeView(View):
    """
    Endpoint which returns either field's api url or choices

    If the model field is a relational field it resolves and returns the endpoint for that fields related_model
    while if it's a choice field, the choices are returned else returns an empty dict
    """
    queryset = None

    @staticmethod
    def __get_filterset_field_data(field, contenttype):
        data = {"type": "others"}

        if isinstance(field, (filters.MultipleChoiceFilter, ModelMultipleChoiceFilter)):
            if "choices" in field.extra:  # Field choices
                # Problem might arise here if plugin developer do not declare field choices using nautobot.utilities.choices.ChoiceSet
                data = {
                    "type": "static-choices",
                    "choices": field.extra["choices"].CHOICES,
                    "allow_multiple": True,
                }
            elif hasattr(field, "queryset"):  # Dynamically populated choices
                if isinstance(field, StatusFilter):
                    related_model = Status
                else:
                    related_model = field.extra["queryset"].model
                api_endpoint = get_model_api_endpoint(related_model)

                if api_endpoint:
                    data = {
                        "type": "dynamic-choices",
                        "data_url": api_endpoint,
                    }
                # Status and Tag api requires content_type, to limit result to only related content_types
                if related_model in [Status, Tag]:
                    data["content_type"] = json.dumps([contenttype])

        elif isinstance(field, (RelatedMembershipBooleanFilter, )):  # Yes / No choice
            data = {
                "type": "static-choices",
                "choices": BOOLEAN_WITH_BLANK_CHOICES,
                "allow_multiple": False,
            }
        return data

    def get(self, request):
        field_name = request.GET.get("field_name")

        contenttype = request.GET.get("contenttype")
        app_label, model_name = contenttype.split(".")
        model = ContentType.objects.get(app_label=app_label, model=model_name).model_class()
        filterset = get_filterset_for_model(model)

        if filterset is None:
            # TODO Timizuo Raise Error if filterset not found
            pass

        field = filterset.base_filters.get(field_name)
        if field is None:
            return JsonResponse({field_name: "Field not found in filterset"}, status=400)

        data = self.__get_filterset_field_data(field, contenttype)

        return JsonResponse(data)
