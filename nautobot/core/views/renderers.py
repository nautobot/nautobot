import logging

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.template import engines, loader
from django.urls import resolve
from django_tables2 import RequestConfig
from rest_framework import renderers

from nautobot.core.constants import MAX_PAGE_SIZE_DEFAULT
from nautobot.core.forms import (
    restrict_form_fields,
    SearchForm,
    TableConfigForm,
)
from nautobot.core.forms.forms import DynamicFilterFormSet
from nautobot.core.templatetags.helpers import bettertitle, validated_viewname
from nautobot.core.utils.config import get_settings_or_config
from nautobot.core.utils.permissions import get_permission_for_model
from nautobot.core.utils.requests import (
    convert_querydict_to_factory_formset_acceptable_querydict,
    normalize_querydict,
)
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.utils import (
    check_filter_for_display,
    common_detail_view_context,
    get_csv_form_fields_from_serializer_class,
    get_saved_views_for_user,
    view_changes_not_saved,
)
from nautobot.extras.models import SavedView
from nautobot.extras.models.change_logging import ObjectChange


class NautobotHTMLRenderer(renderers.BrowsableAPIRenderer):
    """
    Inherited from BrowsableAPIRenderer to do most of the heavy lifting for getting the context needed for templates and template rendering.
    """

    # Log error messages within NautobotHTMLRenderer
    logger = logging.getLogger(__name__)
    saved_view = None

    exception_template_names = ["%(status_code)s.html"]

    def get_dynamic_filter_form(self, view, request, *args, filterset_class=None, **kwargs):
        """
        Helper function to obtain the filter_form_class,
        and then initialize and return the filter_form used in the ObjectListView UI.
        """
        factory_formset_params = {}
        filterset = None
        if filterset_class:
            filterset = filterset_class()
            factory_formset_params = convert_querydict_to_factory_formset_acceptable_querydict(
                view.filter_params if view.filter_params is not None else request.GET, filterset
            )
        return DynamicFilterFormSet(filterset=filterset, data=factory_formset_params)

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
        request = kwargs.get("request", view.request)
        saved_view_pk = request.GET.get("saved_view", None)
        table_changes_pending = request.GET.get("table_changes_pending", False)
        queryset = view.alter_queryset(request)

        if view.action in ["list", "notes", "changelog"]:
            if view.action == "list":
                permissions = kwargs.get("permissions", {})
                self.saved_view = None
                if saved_view_pk is not None:
                    try:
                        # We are not using .restrict(request.user, "view") here
                        # User should be able to see any saved view that he has the list view access to.
                        self.saved_view = SavedView.objects.get(pk=saved_view_pk)
                    except ObjectDoesNotExist:
                        pass
                if view.request.GET.getlist("sort") or (
                    self.saved_view is not None and self.saved_view.config.get("sort_order")
                ):
                    view.hide_hierarchy_ui = True  # hide tree hierarchy if custom sort is used
                table = table_class(
                    queryset,
                    table_changes_pending=table_changes_pending,
                    saved_view=self.saved_view,
                    user=request.user,
                    hide_hierarchy_ui=view.hide_hierarchy_ui,
                )
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
                "per_page": get_paginate_count(request, self.saved_view),
            }
            max_page_size = get_settings_or_config("MAX_PAGE_SIZE", fallback=MAX_PAGE_SIZE_DEFAULT)
            if max_page_size and paginate["per_page"] > max_page_size:
                messages.warning(
                    request,
                    f'Requested "per_page" is too large. No more than {max_page_size} items may be displayed at a time.',
                )
            return RequestConfig(request, paginate).configure(table)
        else:
            pk_list = kwargs.get("pk_list", [])
            table = table_class(queryset.filter(pk__in=pk_list), orderable=False)
            if view.action in ["bulk_destroy", "bulk_update"]:
                # Hide actions column if present
                if "actions" in table.columns:
                    table.columns.hide("actions")
            return table

    def validate_action_buttons(self, view, request):
        """Verify actions in self.action_buttons are valid view actions."""
        queryset = view.alter_queryset(request)
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

    def get_template_context(self, data, renderer_context):
        # borrowed from rest_framework's TemplateHTMLRenderer - should our html renderer be based on that class?
        response = renderer_context["response"]
        if response.exception:
            data["status_code"] = response.status_code
        return data

    def get_exception_template(self, response):
        # borrowed from rest_framework's TemplateHTMLRenderer - remove if switching base class
        template_names = [name % {"status_code": response.status_code} for name in self.exception_template_names]

        try:
            # Try to find an appropriate error template
            return self.resolve_template(template_names)
        except Exception:
            # Fall back to using eg '404 Not Found'
            body = f"{response.status_code} {response.status_text.title()}"
            template = engines["django"].from_string(body)
            return template

    def resolve_template(self, template_names):
        # borrowed from rest_framework's TemplateHTMLRenderer - remove if switching base class
        return loader.select_template(template_names)

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
        # Check if queryset attribute is set before doing anything
        queryset = view.alter_queryset(request)
        model = queryset.model
        form_class = view.get_form_class()
        content_type = ContentType.objects.get_for_model(model)
        form = None
        table = None
        search_form = None
        instance = None
        filter_form = None
        display_filter_params = []
        # Compile a dictionary indicating which permissions are available to the current user for this model
        permissions = self.construct_user_permissions(request, model)
        if view.detail or view.action == "create":
            instance = view.get_object()
            return_url = view.get_return_url(request, instance)
        else:
            return_url = view.get_return_url(request)
        # Get form for context rendering according to view.action unless it is previously set.
        # A form will be passed in from the views if the form has errors.
        if data.get("form"):
            form = data["form"]
        else:
            if view.action == "list":
                if view.filterset_class is not None:
                    view.queryset = view.filter_queryset(queryset)
                    if view.filterset is not None:
                        filterset_filters = view.filterset.filters
                    else:
                        filterset_filters = view.filterset_class.get_filters()
                    display_filter_params = [
                        check_filter_for_display(filterset_filters, field_name, values)
                        for field_name, values in view.filter_params.items()
                    ]
                    if view.filterset_form_class is not None:
                        filter_form = view.filterset_form_class(view.filter_params, label_suffix="")
                table = self.construct_table(view, request=request, permissions=permissions)
                q_placeholder = "Search " + bettertitle(model._meta.verbose_name_plural)
                search_form = SearchForm(data=view.filter_params, q_placeholder=q_placeholder)
            elif view.action == "destroy":
                form = form_class(initial=request.GET)
            elif view.action in ["create", "update"]:
                initial_data = normalize_querydict(request.GET, form_class=form_class)
                form = form_class(instance=instance, initial=initial_data)
                restrict_form_fields(form, request.user)
            elif view.action == "bulk_destroy":
                pk_list = getattr(view, "pk_list", [])
                initial = {
                    "pk": pk_list,
                    "return_url": return_url,
                }
                form = form_class(initial=initial)
                delete_all = request.POST.get("_all")
                if not delete_all:
                    table = self.construct_table(view, pk_list=pk_list)
            elif view.action == "bulk_create":  # 3.0 TODO: remove, replaced by ImportObjects system Job
                form = view.get_form()
                if request.data:
                    table = data.get("table")
            elif view.action == "bulk_update":
                edit_all = request.POST.get("_all")
                pk_list = getattr(view, "pk_list", [])
                if pk_list or edit_all:
                    initial_data = {"pk": pk_list}
                    form = form_class(model, initial=initial_data, edit_all=edit_all)
                    restrict_form_fields(form, request.user)
                if not edit_all:
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
            "content_type": content_type,
            "model": model,
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
            "view_action": view.action,
            "detail": False,
        }

        self._set_context_from_method(view, "get_view_titles", context, "view_titles")
        self._set_context_from_method(view, "get_breadcrumbs", context, "breadcrumbs")

        if view.detail:
            # If we are in a retrieve related detail view (retrieve and custom actions).
            try:
                context["object_detail_content"] = view.object_detail_content
            except AttributeError:
                # If the view does not have a object_detail_content attribute, set it to None.
                context["object_detail_content"] = None
            context.update(common_detail_view_context(request, instance))
        if view.action == "list":
            # Construct valid actions for list view.
            valid_actions = self.validate_action_buttons(view, request)
            # Query SavedViews for dropdown button
            resolved_path = resolve(request.path)
            list_url = f"{resolved_path.app_name}:{resolved_path.url_name}"
            saved_views = None
            if model.is_saved_view_model:
                saved_views = get_saved_views_for_user(request.user, list_url)

            new_changes_not_applied = view_changes_not_saved(request, view, self.saved_view)
            context.update(
                {
                    "current_saved_view": self.saved_view,
                    "new_changes_not_applied": new_changes_not_applied,
                    "action_buttons": valid_actions,
                    "list_url": list_url,
                    "saved_views": saved_views,
                    "title": bettertitle(model._meta.verbose_name_plural),
                }
            )
        elif view.action in ["create", "update"]:
            context.update(
                {
                    "editing": instance.present_in_database,
                }
            )
        elif view.action == "bulk_create":  # 3.0 TODO: remove, replaced by ImportObjects system Job
            context.update(
                {
                    "active_tab": view.bulk_create_active_tab if view.bulk_create_active_tab else "csv-data",
                    "fields": get_csv_form_fields_from_serializer_class(view.serializer_class),
                }
            )

        # Ensure the proper inheritance of context variables is applied: the view's returned data takes priority over the viewset's get_extra_context
        context.update(view.get_extra_context(request, instance))
        context.update(self.get_template_context(data, renderer_context))

        return context

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Overrode render() from BrowsableAPIRenderer to set self.template with NautobotViewSet's get_template_name() before it is rendered.
        """
        view = renderer_context["view"]
        request = renderer_context["request"]
        response = renderer_context["response"]

        # TODO: borrowed from TemplateHTMLRenderer. Remove when switching base class
        if response.exception:
            template = self.get_exception_template(response)
            context = self.get_context(data, accepted_media_type, renderer_context)
            return template.render(context, request=request)

        # Get the corresponding template based on self.action in view.get_template_name() unless it is already specified in the Response() data.
        # See form_valid() for self.action == "bulk_create".
        self.template = data.get("template", view.get_template_name())

        return super().render(data, accepted_media_type=accepted_media_type, renderer_context=renderer_context)

    @staticmethod
    def _set_context_from_method(
        view,
        view_function,
        context,
        context_key,
    ):
        try:
            context[context_key] = getattr(view, view_function)()
        except AttributeError:
            context[context_key] = None
