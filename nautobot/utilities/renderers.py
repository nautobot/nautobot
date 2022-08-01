from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django_tables2 import RequestConfig

from rest_framework import renderers

from nautobot.utilities.permissions import get_permission_for_model
from nautobot.utilities.forms import (
    ConfirmationForm,
    TableConfigForm,
    restrict_form_fields,
)
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.templatetags.helpers import validated_viewname
from nautobot.utilities.utils import (
    normalize_querydict,
)

ACTION_TO_VIEW_TYPE = {
    "list": "list",
    "retrieve": "detail",
    "destroy": "delete",
    "create_or_update": "edit",
    "bulk_create": "bulk_import",
    "bulk_destroy": "bulk_delete",
    "bulk_edit": "bulk_edit",
}


class NautobotHTMLRenderer(renderers.BrowsableAPIRenderer):
    template = None
    default_return_url = None
    table = None

    def get_return_url(self, request, view, obj=None):

        # First, see if `return_url` was specified as a query parameter or form data. Use this URL only if it's
        # considered safe.
        query_param = request.GET.get("return_url") or request.POST.get("return_url")
        if query_param and is_safe_url(url=query_param, allowed_hosts=request.get_host()):
            return query_param

        # Next, check if the object being modified (if any) has an absolute URL.
        # Note that the use of both `obj.present_in_database` and `obj.pk` is correct here because this conditional
        # handles all three of the create, update, and delete operations. When Django deletes an instance
        # from the DB, it sets the instance's PK field to None, regardless of the use of a UUID.
        if obj is not None and obj.present_in_database and obj.pk and hasattr(obj, "get_absolute_url"):
            return obj.get_absolute_url()

        # Fall back to the default URL (if specified) for the view.
        if self.default_return_url is not None:
            return reverse(self.default_return_url)

        # Attempt to dynamically resolve the list view for the object
        if hasattr(view, "queryset"):
            model_opts = view.queryset.model._meta
            try:
                prefix = "plugins:" if model_opts.app_label in settings.PLUGINS else ""
                return reverse(f"{prefix}{model_opts.app_label}:{model_opts.model_name}_list")
            except NoReverseMatch:
                pass

        # If all else fails, return home. Ideally this should never happen.
        return reverse("home")

    def construct_user_permissions(self, request, model):
        permissions = {}
        for action in ("add", "change", "delete", "view"):
            perm_name = get_permission_for_model(model, action)
            permissions[action] = request.user.has_perm(perm_name)
        return permissions

    def construct_table(self, request, queryset, permissions):
        table = self.table(queryset, user=request.user)
        if "pk" in table.base_columns and (permissions["change"] or permissions["delete"]):
            table.columns.show("pk")

        # Apply the request context
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        return RequestConfig(request, paginate).configure(table)

    def validate_action_buttons(self, view, request):
        """Verify actions in self.action_buttons are valid view actions."""

        always_valid_actions = ("export",)
        valid_actions = []
        invalid_actions = []

        for action in view.action_buttons:
            if action in always_valid_actions or validated_viewname(view.queryset.model, action) is not None:
                valid_actions.append(action)
            else:
                invalid_actions.append(action)
        if invalid_actions:
            messages.error(request, f"Missing views for action(s) {', '.join(invalid_actions)}")
        return valid_actions

    def validate_action_buttons(self, view, request):
        """Verify actions in self.action_buttons are valid view actions."""

        always_valid_actions = ("export",)
        valid_actions = []
        invalid_actions = []

        for action in view.action_buttons:
            if action in always_valid_actions or validated_viewname(view.queryset.model, action) is not None:
                valid_actions.append(action)
            else:
                invalid_actions.append(action)
        if invalid_actions:
            messages.error(request, f"Missing views for action(s) {', '.join(invalid_actions)}")
        return valid_actions

    def construct_user_permissions(self, request, model):
        permissions = {}
        for action in ("add", "change", "delete", "view"):
            perm_name = get_permission_for_model(model, action)
            permissions[action] = request.user.has_perm(perm_name)
        return permissions

    def construct_table(self, view, request, permissions):
        table = view.table(view.queryset, user=request.user)
        if "pk" in table.base_columns and (permissions["change"] or permissions["delete"]):
            table.columns.show("pk")

        # Apply the request context
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        return RequestConfig(request, paginate).configure(table)

    def get_context(self, data, accepted_media_type, renderer_context):
        view = renderer_context["view"]
        request = renderer_context["request"]
        instance = view.get_object()
        model = view.queryset.model
        content_type = ContentType.objects.get_for_model(model)
        view.queryset = view.filterset(request.GET, view.queryset).qs
        view.queryset = view.alter_queryset(request)
        # Compile a dictionary indicating which permissions are available to the current user for this model
        permissions = self.construct_user_permissions(request, model)
        # Construct the objects table
        valid_actions = self.validate_action_buttons(view, request)
        detail_context = view.get_extra_context(request, "detail", instance)
        obj = view.alter_obj_for_edit(instance, request, view.args, view.kwargs)
        form = None
        table = None

        if data.get("form"):
            form = data["form"]
        else:
            if view.action == "list":
                table = self.construct_table(view, request, permissions)
            elif view.action == "destroy":
                form = ConfirmationForm(initial=request.GET)
            elif view.action == "create_or_update":
                initial_data = normalize_querydict(request.GET)
                form = view.form(instance=obj, initial=initial_data)
                restrict_form_fields(form, request.user)
            elif view.action == "bulk_destroy":
                if request.POST.get("_all"):
                    if view.bulk_delete_filterset is not None:
                        pk_list = [
                            obj.pk for obj in self.bulk_delete_filterset(request.GET, model.objects.only("pk")).qs
                        ]
                    else:
                        pk_list = model.objects.values_list("pk", flat=True)
                else:
                    form_cls = view.get_form()
                    pk_list = request.POST.getlist("pk")
                    # form = form_cls(request.POST)
                    form = form_cls(
                        initial={
                            "pk": pk_list,
                            "return_url": view.get_return_url(request),
                        }
                    )
            elif view.action == "bulk_create":
                form = view._import_form_for_bulk_import()
            elif view.action == "bulk_edit":
                if request.POST.get("_all") and view.bulk_edit_filterset is not None:
                    pk_list = [obj.pk for obj in view.bulk_edit_filterset(request.GET, view.queryset.only("pk")).qs]
                else:
                    pk_list = request.POST.getlist("pk")
                if "_apply" in request.POST:
                    form = view.bulk_edit_form(model, request.POST)
                    restrict_form_fields(form, request.user)
                else:
                    # Include the PK list as initial data for the form
                    initial_data = {"pk": pk_list}
                    # Check for other contextual data needed for the form. We avoid passing all of request.GET because the
                    # filter values will conflict with the bulk edit form fields.
                    # TODO: Find a better way to accomplish this
                    if "device" in request.GET:
                        initial_data["device"] = request.GET.get("device")
                    elif "device_type" in request.GET:
                        initial_data["device_type"] = request.GET.get("device_type")

                    form = view.bulk_edit_form(model, initial=initial_data)
                    restrict_form_fields(form, request.user)

        context = {
            "obj": obj,
            "object": instance,
            "obj_type": view.queryset.model._meta.verbose_name,
            "obj_type_plural": view.queryset.model._meta.verbose_name_plural,
            "editing": obj.present_in_database,
            "form": form,
            "fields": view.import_form().fields,
            "table": table if table else data.get("table", None),
            "return_url": view.get_return_url(request, instance),
            "verbose_name": view.queryset.model._meta.verbose_name,
            "verbose_name_plural": view.queryset.model._meta.verbose_name_plural,
            "changelog_url": view.get_changelog_url(instance),
            "content_type": content_type,
            "permissions": permissions,
            "action_buttons": valid_actions,
            "table_config_form": TableConfigForm(table=table) if table else None,
            "filter_form": view.filterset_form(request.GET, label_suffix="") if view.filterset_form else None,
            "active_tab": "csv-data",
            **detail_context,
        }
        context.update(view.get_extra_context(request, ACTION_TO_VIEW_TYPE[view.action], instance=None))
        return context

    def render(self, data, accepted_media_type=None, renderer_context=None):
        view = renderer_context["view"]
        if data.get("template"):
            self.template = data["template"]
        else:
            self.template = view.get_template_name(ACTION_TO_VIEW_TYPE[view.action])
        return super().render(data, accepted_media_type=accepted_media_type, renderer_context=renderer_context)
