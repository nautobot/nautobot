import logging

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.safestring import mark_safe
from django_tables2 import RequestConfig
from rest_framework import renderers

from nautobot.core.forms import SearchForm
from nautobot.extras.models.change_logging import ChangeLoggedModel, ObjectChange
from nautobot.extras.utils import get_base_template
from nautobot.utilities.forms import (
    TableConfigForm,
    restrict_form_fields,
)
from nautobot.utilities.forms.forms import DynamicFilterFormSet
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.permissions import get_permission_for_model
from nautobot.utilities.templatetags.helpers import bettertitle, validated_viewname
from nautobot.utilities.utils import (
    convert_querydict_to_factory_formset_acceptable_querydict,
    normalize_querydict,
    get_filterable_params_from_filter_params,
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
        return get_filterable_params_from_filter_params(filter_params, view.non_filter_params, view.filterset_class)

    def get_dynamic_filter_form(self, view, request, *args, filterset_class=None, **kwargs):
        """
        Helper function to obtain the filter_form_class,
        and then initialize and return the filter_form used in the ObjectListView UI.
        """
        factory_formset_params = {}
        if filterset_class:
            factory_formset_params = convert_querydict_to_factory_formset_acceptable_querydict(
                request.GET, filterset_class
            )
        return DynamicFilterFormSet(filterset_class=view.filterset_class, data=factory_formset_params)

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
        if view.action in ["list", "notes", "changelog"]:
            request = kwargs.get("request", view.request)
            if view.action == "list":
                permissions = kwargs.get("permissions", {})
                table = table_class(queryset, user=request.user)
                if "pk" in table.base_columns and (permissions["change"] or permissions["delete"]):
                    table.columns.show("pk")
            elif view.action == "notes":
                obj = kwargs.get("object")
                table = table_class(obj.notes, user=request.user)
            elif view.action == "changelog":
                obj = kwargs.get("object")
                content_type = kwargs.get("content_type")
                objectchanges = (
                    ObjectChange.objects.restrict(request.user, "view")
                    .prefetch_related("user", "changed_object_type")
                    .filter(
                        Q(changed_object_type=content_type, changed_object_id=obj.pk)
                        | Q(related_object_type=content_type, related_object_id=obj.pk)
                    )
                )
                table = table_class(data=objectchanges, orderable=False)

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
        search_form = None
        changelog_url = None
        instance = None
        filter_form = None
        queryset = view.alter_queryset(request)
        display_filter_params = []
        # Compile a dictionary indicating which permissions are available to the current user for this model
        permissions = self.construct_user_permissions(request, model)
        if view.action in ["create", "retrieve", "update", "destroy", "changelog", "notes"]:
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

                    display_filter_params = [
                        [field_name, values if isinstance(values, (list, tuple)) else [values]]
                        for field_name, values in filter_params.items()
                    ]
                    if view.filterset_form_class is not None:
                        filter_form = view.filterset_form_class(request.GET, label_suffix="")
                table = self.construct_table(view, request=request, permissions=permissions)
                search_form = SearchForm(data=request.GET)
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
            elif view.action == "notes":
                initial_data = {
                    "assigned_object_type": content_type,
                    "assigned_object_id": instance.pk,
                }
                form = form_class(initial=initial_data)
                table = self.construct_table(view, object=instance)
            elif view.action == "changelog":
                table = self.construct_table(view, object=instance, content_type=content_type)

        context = {
            "changelog_url": changelog_url,  # NOTE: This context key is deprecated in favor of `object.get_changelog_url`.
            "content_type": content_type,
            "form": form,
            "filter_form": filter_form,
            "dynamic_filter_form": self.get_dynamic_filter_form(view, request, filterset_class=view.filterset_class),
            "search_form": search_form,
            "filter_params": display_filter_params,
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
                        "list_url": validated_viewname(model, "list"),
                        "title": bettertitle(model._meta.verbose_name_plural),
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
                        "active_tab": view.bulk_create_active_tab if view.bulk_create_active_tab else "csv-data",
                        "fields": view.bulk_create_form_class(model).fields if view.bulk_create_form_class else None,
                    }
                )
            elif view.action in ["changelog", "notes"]:
                context.update(
                    {
                        "base_template": get_base_template(data.get("base_template"), model),
                        "active_tab": view.action,
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
