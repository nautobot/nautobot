from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse, NoReverseMatch
from django.utils.http import is_safe_url
from django_tables2 import RequestConfig
from rest_framework import renderers

from nautobot.utilities.forms import (
    ConfirmationForm,
    TableConfigForm,
    restrict_form_fields,
)
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.permissions import get_permission_for_model
from nautobot.utilities.templatetags.helpers import validated_viewname


class NautobotHTMLRender(renderers.BrowsableAPIRenderer):
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

    def get_context(self, data, accepted_media_type, renderer_context):
        context = super().get_context(data, accepted_media_type, renderer_context)

        view = renderer_context['view']
        request = renderer_context['request']
        response = renderer_context['response']

        queryset = view.queryset
        model = queryset.model
        permissions = self.construct_user_permissions(request, model)
        from nautobot.circuits.tables import CircuitTable
        self.table = CircuitTable
        table = self.construct_table(request, queryset, permissions)
        valid_actions = self.validate_action_buttons(view, request)

        obj = view.get_object()

        #
        # This is literally just cheating and using the existing Form object,
        # and skimming over all of the code that uses the serializer to generate
        # a form.
        #
        from nautobot.dcim.forms import SiteForm
        form = SiteForm(instance=obj, initial=request.data)

        # from nautobot.utilities.forms import ConfirmationForm
        # delete_form = ConfirmationForm(initial=request.data)


        #
        # This renders the form as HTML, so the `dcim/site_edit.html` template
        # needs the "form" block to just have {{ form }} as the content
        # rendering this context variable directly as HTML.
        #
        # form = self.get_rendered_html_form(data, view, 'GET', request)

        # This is trying to either generate a form class from the serializer, or
        # just render the form fields using the serializer in the tempalte
        # context. There is work to do here to demystify `{% render_field
        # serialier.foo style=style %}` e.g. What is style and how do we use it
        # to determine the widgets/templates used to render the field properly?
        # form_class = self.get_raw_data_form(data, view, 'GET', request)
        # form_class = form_class.__class__
        '''
        style = renderer_context.get("style", {})
        if 'template_pack' not in style:
            style['template_pack'] = 'rest_framework/vertical/'
        style['renderer'] = renderers.HTMLFormRenderer()
        '''
        # template_name = view.get_template_name(view.action),
        # template_name = self.template
        # breakpoint()
        # self.template = template_name

        content_type = ContentType.objects.get_for_model(model)

        context.update({
            "obj": obj,
            "object": obj,
            "obj_type": model._meta.verbose_name,
            "obj_type_plural": model._meta.verbose_name_plural,
            # "form": data.serializer,
            "form": form,
            "return_url": self.get_return_url(request, view, obj),
            "editing": obj.present_in_database,
            "template": self.template,
            # "serializer": data.serializer,
            # "style": style,
            "content_type": content_type,
            "table": table,
            "permissions": permissions,
            "action_buttons": valid_actions,
            "table_config_form": TableConfigForm(table=table),
            "filter_form": view.filterset_form(request.data, label_suffix="") if view.filterset_form else None,
        })

        return context

    def render(self, data, accepted_media_type=None, renderer_context=None):
        view = renderer_context['view']
        # request = renderer_context['request']
        # response = renderer_context['response']
        # breakpoint()
        self.template = view.get_template_name(view.action)
        return super().render(data, accepted_media_type=accepted_media_type, renderer_context=renderer_context)
