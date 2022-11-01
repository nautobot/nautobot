import logging

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe
from django_tables2 import RequestConfig
from rest_framework import renderers

from nautobot.extras.models.change_logging import ChangeLoggedModel
from nautobot.utilities.forms import (
    TableConfigForm,
    restrict_form_fields,
)
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.permissions import get_permission_for_model
from nautobot.utilities.templatetags.helpers import validated_viewname
from nautobot.utilities.utils import (
    normalize_querydict,
)


class NautobotHTMLRenderer(renderers.BrowsableAPIRenderer):
    """
    Inherited from BrowsableAPIRenderer to do most of the heavy lifting for getting the context needed for templates and template rendering.
    """

    # Log error messages within NautobotHTMLRenderer
    logger = logging.getLogger(__name__)

    def get_filter_params(self, view, request):
        """Helper function - take request.GET and discard any parameters that are not used for queryset filtering."""
        filter_params = request.GET.copy()
        for non_filter_param in view.non_filter_params:
            filter_params.pop(non_filter_param, None)
        return filter_params

    def get_filter_form(self, view, request, *args, **kwargs):
        """
        Helper function to obtain the filter_form_class if there is one,
        and then initialize and return the filter_form used in the ObjectListView UI.
        """
        if view.filterset_form_class is not None:
            return view.filterset_form_class(request.GET, label_suffix="", *args, **kwargs)
        else:
            return None

    def construct_user_permissions(self, request, model):
        """
        Helper function to gather the user's permissions to add, change, delete and view the model,
        and then render the action buttons accordingly allowed in the ObjectListView UI.
        """
        permissions = {}
        for action in ("add", "change", "delete", "view"):
            perm_name = get_permission_for_model(model, action)
            permissions[action] = request.user.has_perm(perm_name)
        return permissions

    def construct_table(self, view, **kwargs):
        """
        Helper function to construct and paginate the table for rendering used in the ObjectListView, ObjectBulkUpdateView and ObjectBulkDestroyView.
        """
        table_class = view.get_table_class()
        queryset = view.get_queryset()
        if view.action == "list":
            permissions = kwargs.get("permissions", {})
            request = kwargs.get("request", view.request)
            table = table_class(queryset, user=request.user)
            if "pk" in table.base_columns and (permissions["change"] or permissions["delete"]):
                table.columns.show("pk")
            # Apply the request context
            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            return RequestConfig(request, paginate).configure(table)
        else:
            pk_list = kwargs.get("pk_list", [])
            table = table_class(queryset.filter(pk__in=pk_list), orderable=False)
            return table

    def validate_action_buttons(self, view, request):
        """Verify actions in self.action_buttons are valid view actions."""
        queryset = view.get_queryset()
        always_valid_actions = ("export",)
        valid_actions = []
        invalid_actions = []
        # added check for whether the action_buttons exist because of issue #2107
        if view.action_buttons is None:
            view.action_buttons = []
        for action in view.action_buttons:
            if action in always_valid_actions or validated_viewname(queryset.model, action) is not None:
                valid_actions.append(action)
            else:
                invalid_actions.append(action)
        if invalid_actions:
            messages.error(request, f"Missing views for action(s) {', '.join(invalid_actions)}")
        return valid_actions

    def get_context(self, data, accepted_media_type, renderer_context):
        """
        Override get_context() from BrowsableAPIRenderer to obtain the context data we need to render our templates.
        context variable contains template context needed to render Nautobot generic templates / circuits templates.
        Override this function to add additional key/value pair to pass it to your templates.
        """
        if renderer_context is None:
            # renderer_context content is automatically provided with the view returning the Response({}) object.
            # The only way renderer_context is None if the user directly calls it from the renderer without a view.
            self.logger.debug(
                "renderer_context is None, please do not directly call get_context() from NautobotHTMLRenderer without specifying the view."
            )
            return {}
        view = renderer_context["view"]
        request = renderer_context["request"]
        # Check if queryset attribute is set before doing anything.
        queryset = view.get_queryset()
        model = queryset.model
        form_class = view.get_form_class()
        content_type = ContentType.objects.get_for_model(model)
        form = None
        table = None
        changelog_url = None
        instance = None
        queryset = view.alter_queryset(request)
        # Compile a dictionary indicating which permissions are available to the current user for this model
        permissions = self.construct_user_permissions(request, model)
        if view.action in ["create", "retrieve", "update", "destroy"]:
            instance = view.get_object()
            return_url = view.get_return_url(request, instance)
            if isinstance(instance, ChangeLoggedModel):
                changelog_url = instance.get_changelog_url()
        else:
            return_url = view.get_return_url(request)
        # Get form for context rendering according to view.action unless it is previously set.
        # A form will be passed in from the views if the form has errors.
        if data.get("form"):
            form = data["form"]
        else:
            if view.action == "list":
                filter_params = self.get_filter_params(view, request)
                if view.filterset_class is not None:
                    filterset = view.filterset_class(filter_params, view.queryset)
                    view.queryset = filterset.qs
                    if not filterset.is_valid():
                        messages.error(
                            request,
                            mark_safe(f"Invalid filters were specified: {filterset.errors}"),
                        )
                        view.queryset = view.queryset.none()
                table = self.construct_table(view, request=request, permissions=permissions)
            elif view.action == "destroy":
                form = form_class(initial=request.GET)
            elif view.action in ["create", "update"]:
                initial_data = normalize_querydict(request.GET)
                form = form_class(instance=instance, initial=initial_data)
                restrict_form_fields(form, request.user)
            elif view.action == "bulk_destroy":
                pk_list = getattr(view, "pk_list", [])
                if pk_list:
                    initial = {
                        "pk": pk_list,
                        "return_url": return_url,
                    }
                    form = form_class(initial=initial)
                table = self.construct_table(view, pk_list=pk_list)
            elif view.action == "bulk_create":
                form = view.get_form()
                if request.data:
                    table = data.get("table")
            elif view.action == "bulk_update":
                pk_list = getattr(view, "pk_list", [])
                if pk_list:
                    initial_data = {"pk": pk_list}
                    form = form_class(model, initial=initial_data)

                    restrict_form_fields(form, request.user)
                table = self.construct_table(view, pk_list=pk_list)

        context = {
            "changelog_url": changelog_url,  # NOTE: This context key is deprecated in favor of `object.get_changelog_url`.
            "content_type": content_type,
            "form": form,
            "filter_form": self.get_filter_form(view, request),
            "object": instance,
            "obj": instance,  # NOTE: This context key is deprecated in favor of `object`.
            "obj_type": queryset.model._meta.verbose_name,  # NOTE: This context key is deprecated in favor of `verbose_name`.
            "obj_type_plural": queryset.model._meta.verbose_name_plural,  # NOTE: This context key is deprecated in favor of `verbose_name_plural`.
            "permissions": permissions,
            "return_url": return_url,
            "table": table if table is not None else data.get("table", None),
            "table_config_form": TableConfigForm(table=table) if table else None,
            "verbose_name": queryset.model._meta.verbose_name,
            "verbose_name_plural": queryset.model._meta.verbose_name_plural,
        }
        if view.action == "retrieve":
            context.update(view.get_extra_context(request, instance))
        else:
            if view.action == "list":
                # Construct valid actions for list view.
                valid_actions = self.validate_action_buttons(view, request)
                context.update(
                    {
                        "action_buttons": valid_actions,
                    }
                )
            elif view.action in ["create", "update"]:
                context.update(
                    {
                        "editing": instance.present_in_database,
                    }
                )
            elif view.action == "bulk_create":
                context.update(
                    {
                        "active_tab": "csv-data",
                        "fields": view.bulk_create_form_class(model).fields if view.bulk_create_form_class else None,
                    }
                )
            context.update(view.get_extra_context(request, instance=None))
        return context

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Overrode render() from BrowsableAPIRenderer to set self.template with NautobotViewSet's get_template_name() before it is rendered.
        """
        view = renderer_context["view"]
        # Get the corresponding template based on self.action in view.get_template_name() unless it is already specified in the Response() data.
        # See form_valid() for self.action == "bulk_create".
        self.template = data.get("template", view.get_template_name())
        return super().render(data, accepted_media_type=accepted_media_type, renderer_context=renderer_context)
