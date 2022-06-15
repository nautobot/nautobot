import logging

from django.db.models import ManyToManyField, ProtectedError
from django.views.generic import View
from django.conf import settings
from django.utils.http import is_safe_url
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.http import HttpResponse
from django.core.exceptions import (
    FieldDoesNotExist,
    ObjectDoesNotExist,
    ValidationError,
)
from django_tables2 import RequestConfig
from rest_framework import viewsets

from .permissions import resolve_permission
from nautobot.utilities.permissions import get_permission_for_model
from nautobot.utilities.views import GetReturnURLMixin, ObjectPermissionRequiredMixin
from nautobot.utilities.templatetags.helpers import validated_viewname
from nautobot.extras.models import CustomField, ExportTemplate
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.error_handlers import handle_protectederror
from nautobot.utilities.forms import (
    BootstrapMixin,
    BulkRenameForm,
    ConfirmationForm,
    CSVDataField,
    CSVFileField,
    ImportForm,
    TableConfigForm,
    restrict_form_fields,
)
from nautobot.utilities.utils import (
    csv_format,
    normalize_querydict,
    prepare_cloned_fields,
)

class NautobotViewSet(viewsets.ModelViewSet, GetReturnURLMixin, ObjectPermissionRequiredMixin, View):
    queryset = None
    serializer_class = None
    template_name = None
    filterset = None
    filterset_form = None
    table = None
    action_buttons = None
    model_form = None

    ## Helper Methods
    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "view")

    def get_template_name(self):
        """
        Return self.template_name if set. Otherwise, resolve the template path by model app_label and name.
        """
        if self.template_name is not None:
            return self.template_name
        model_opts = self.queryset.model._meta
        return f"{model_opts.app_label}/{model_opts.model_name}.html"
    
    def get_extra_context(self, request, instance):
        """
        Return any additional context data for the template.

        Args:
            request: The current request
            instance: The object being viewed

        Returns:
            dict
        """
        return {}

    def get_changelog_url(self, instance):
        """Return the changelog URL for a given instance."""
        meta = self.queryset.model._meta

        # Don't try to generate a changelog_url for an ObjectChange.
        if meta.model_name == "objectchange":
            return None

        route = f"{meta.app_label}:{meta.model_name}_changelog"
        if meta.app_label in settings.PLUGINS:
            route = f"plugins:{route}"

        # Iterate the pk-like fields and try to get a URL, or return None.
        fields = ["pk", "slug"]
        for field in fields:
            if not hasattr(instance, field):
                continue

            try:
                return reverse(route, kwargs={field: getattr(instance, field)})
            except NoReverseMatch:
                continue

        # This object likely doesn't have a changelog route defined.
        return None

    def queryset_to_yaml(self):
        """
        Export the queryset of objects as concatenated YAML documents.
        """
        yaml_data = [obj.to_yaml() for obj in self.queryset]

        return "---\n".join(yaml_data)
    
    def queryset_to_csv(self):
        """
        Export the queryset of objects as comma-separated value (CSV), using the model's to_csv() method.
        """
        csv_data = []
        custom_fields = []

        # Start with the column headers
        headers = self.queryset.model.csv_headers.copy()

        # Add custom field headers, if any
        if hasattr(self.queryset.model, "_custom_field_data"):
            for custom_field in CustomField.objects.get_for_model(self.queryset.model):
                headers.append(custom_field.name)
                custom_fields.append(custom_field.name)

        csv_data.append(",".join(headers))

        # Iterate through the queryset appending each object
        for obj in self.queryset:
            data = obj.to_csv()

            for custom_field in custom_fields:
                data += (obj.cf.get(custom_field, ""),)

            csv_data.append(csv_format(data))

        return "\n".join(csv_data)
    
    def validate_action_buttons(self, request):
        """Verify actions in self.action_buttons are valid view actions."""

        always_valid_actions = ("export",)
        valid_actions = []
        invalid_actions = []

        for action in self.action_buttons:
            if action in always_valid_actions or validated_viewname(self.queryset.model, action) is not None:
                valid_actions.append(action)
            else:
                invalid_actions.append(action)
        if invalid_actions:
            messages.error(request, f"Missing views for action(s) {', '.join(invalid_actions)}")
        return valid_actions

    def alter_queryset(self, request):
        # .all() is necessary to avoid caching queries
        return self.queryset.all()

    def extra_context(self):
        return {}
    
    def get_object(self, kwargs):
        """Retrieve an object based on `kwargs`."""
        # Look up an existing object by slug or PK, or name if provided.
        for field in ("slug", "pk", "name"):
            if field in kwargs:
                return get_object_or_404(self.queryset, **{field: kwargs[field]})
        return self.queryset.model()
    
    def alter_obj(self, obj, request, url_args, url_kwargs):
        # Allow views to add extra info to an object before it is processed. For example, a parent object can be defined
        # given some parameter from the request URL.
        return obj

    def dispatch(self, request, *args, **kwargs):
        # Determine required permission based on whether we are editing an existing object
        self._permission_action = "change" if kwargs else "add"

        return super().dispatch(request, *args, **kwargs)
    ## Actual Methods: Detail, List, Edit, Delete Views.

    def retrieve(self, request, *args, **kwargs):
        instance = get_object_or_404(self.queryset, **kwargs)
        return render(
            request,
            self.get_template_name(),
            {
                "object": instance,
                "verbose_name": self.queryset.model._meta.verbose_name,
                "verbose_name_plural": self.queryset.model._meta.verbose_name_plural,
                "changelog_url": self.get_changelog_url(instance),
                **self.get_extra_context(request, instance),
            },
        )
    
    def list(self, request, *args, **kwargs):
        self.template_name = "generic/object_list.html"
        self.action_buttons = ("add", "import", "export")
        model = self.queryset.model
        content_type = ContentType.objects.get_for_model(model)

        if self.filterset:
            self.queryset = self.filterset(request.GET, self.queryset).qs

        # Check for export template rendering
        if request.GET.get("export"):
            et = get_object_or_404(
                ExportTemplate,
                content_type=content_type,
                name=request.GET.get("export"),
            )
            try:
                return et.render_to_response(self.queryset)
            except Exception as e:
                messages.error(
                    request,
                    "There was an error rendering the selected export template ({}): {}".format(et.name, e),
                )

        # Check for YAML export support
        elif "export" in request.GET and hasattr(model, "to_yaml"):
            response = HttpResponse(self.queryset_to_yaml(), content_type="text/yaml")
            filename = "{}{}.yaml".format(
                settings.BRANDING_PREPENDED_FILENAME, self.queryset.model._meta.verbose_name_plural
            )
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
            return response

        # Fall back to built-in CSV formatting if export requested but no template specified
        elif "export" in request.GET and hasattr(model, "to_csv"):
            response = HttpResponse(self.queryset_to_csv(), content_type="text/csv")
            filename = "{}{}.csv".format(
                settings.BRANDING_PREPENDED_FILENAME, self.queryset.model._meta.verbose_name_plural
            )
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
            return response

        # Provide a hook to tweak the queryset based on the request immediately prior to rendering the object list
        self.queryset = self.alter_queryset(request)

        # Compile a dictionary indicating which permissions are available to the current user for this model
        permissions = {}
        for action in ("add", "change", "delete", "view"):
            perm_name = get_permission_for_model(model, action)
            permissions[action] = request.user.has_perm(perm_name)

        # Construct the objects table
        table = self.table(self.queryset, user=request.user)
        if "pk" in table.base_columns and (permissions["change"] or permissions["delete"]):
            table.columns.show("pk")

        # Apply the request context
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(table)

        filter_form = None
        if self.filterset_form:
            if request.GET:
                # Bind form to the values specified in request.GET
                filter_form = self.filterset_form(request.GET, label_suffix="")
            else:
                # Use unbound form with default (initial) values
                filter_form = self.filterset_form(label_suffix="")

        valid_actions = self.validate_action_buttons(request)

        context = {
            "content_type": content_type,
            "table": table,
            "permissions": permissions,
            "action_buttons": valid_actions,
            "table_config_form": TableConfigForm(table=table),
            "filter_form": filter_form,
        }
        context.update(self.extra_context())

        return render(request, self.template_name, context)

    def destroy(self, request, *args, **kwargs):
        print("hey")
        self.template_name = "generic/object_delete.html"
        obj = self.get_object(kwargs)
        print(request.GET)
        form = ConfirmationForm(initial=request.GET)

        return render(
            request,
            self.template_name,
            {
                "obj": obj,
                "form": form,
                "obj_type": self.queryset.model._meta.verbose_name,
                "return_url": self.get_return_url(request, obj),
            },
        )

    def perform_destroy(self, request, **kwargs):
        logger = logging.getLogger("nautobot.views.ObjectDeleteView")
        obj = self.get_object(kwargs)
        form = ConfirmationForm(request.POST)

        if form.is_valid():
            logger.debug("Form validation was successful")

            try:
                obj.delete()
            except ProtectedError as e:
                logger.info("Caught ProtectedError while attempting to delete object")
                handle_protectederror([obj], request, e)
                return redirect(obj.get_absolute_url())

            msg = "Deleted {} {}".format(self.queryset.model._meta.verbose_name, obj)
            logger.info(msg)
            messages.success(request, msg)

            return_url = form.cleaned_data.get("return_url")
            if return_url is not None and is_safe_url(url=return_url, allowed_hosts=request.get_host()):
                return redirect(return_url)
            else:
                return redirect(self.get_return_url(request, obj))

        else:
            logger.debug("Form validation failed")

        return render(
            request,
            self.template_name,
            {
                "obj": obj,
                "form": form,
                "obj_type": self.queryset.model._meta.verbose_name,
                "return_url": self.get_return_url(request, obj),
            },
        )

    def update(self, request, *args, **kwargs):
        self.template_name = "generic/object_edit.html"
        obj = self.alter_obj(self.get_object(kwargs), request, args, kwargs)

        initial_data = normalize_querydict(request.GET)
        form = self.model_form(instance=obj, initial=initial_data)
        restrict_form_fields(form, request.user)

        return render(
            request,
            self.template_name,
            {
                "obj": obj,
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": form,
                "return_url": self.get_return_url(request, obj),
                "editing": obj.present_in_database,
                **self.get_extra_context(request, obj),
            },
        )
    
    def perform_update(self, request, *args, **kwargs):
        logger = logging.getLogger("nautobot.views.ObjectEditView")
        obj = self.alter_obj(self.get_object(kwargs), request, args, kwargs)
        form = self.model_form(data=request.POST, files=request.FILES, instance=obj)
        restrict_form_fields(form, request.user)

        if form.is_valid():
            logger.debug("Form validation was successful")

            try:
                with transaction.atomic():
                    object_created = not form.instance.present_in_database
                    obj = form.save()

                    # Check that the new object conforms with any assigned object-level permissions
                    self.queryset.get(pk=obj.pk)

                msg = "{} {}".format(
                    "Created" if object_created else "Modified",
                    self.queryset.model._meta.verbose_name,
                )
                logger.info(f"{msg} {obj} (PK: {obj.pk})")
                if hasattr(obj, "get_absolute_url"):
                    msg = '{} <a href="{}">{}</a>'.format(msg, obj.get_absolute_url(), escape(obj))
                else:
                    msg = "{} {}".format(msg, escape(obj))
                messages.success(request, mark_safe(msg))

                if "_addanother" in request.POST:

                    # If the object has clone_fields, pre-populate a new instance of the form
                    if hasattr(obj, "clone_fields"):
                        url = "{}?{}".format(request.path, prepare_cloned_fields(obj))
                        return redirect(url)

                    return redirect(request.get_full_path())

                return_url = form.cleaned_data.get("return_url")
                if return_url is not None and is_safe_url(url=return_url, allowed_hosts=request.get_host()):
                    return redirect(return_url)
                else:
                    return redirect(self.get_return_url(request, obj))

            except ObjectDoesNotExist:
                msg = "Object save failed due to object-level permissions violation"
                logger.debug(msg)
                form.add_error(None, msg)

        else:
            logger.debug("Form validation failed")

        return render(
            request,
            self.template_name,
            {
                "obj": obj,
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": form,
                "return_url": self.get_return_url(request, obj),
                "editing": obj.present_in_database,
                **self.get_extra_context(request, obj),
            },
        )
