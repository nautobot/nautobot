import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import (
    FieldDoesNotExist,
    ObjectDoesNotExist,
    ValidationError,
)
from django.db import transaction
from django.db.models import ManyToManyField, ProtectedError
from django.forms import Form, ModelMultipleChoiceField, MultipleHiddenInput, Textarea
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import select_template, TemplateDoesNotExist
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.http import is_safe_url
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormView

from rest_framework import generics, mixins
from rest_framework.response import Response
from rest_framework.viewsets import ViewSetMixin

from nautobot.core.views import mixins as bulk_mixins
from nautobot.extras.models import CustomField, ExportTemplate, ChangeLoggedModel
from nautobot.utilities.error_handlers import handle_protectederror
from nautobot.utilities.forms import (
    BootstrapMixin,
    ConfirmationForm,
    CSVDataField,
    CSVFileField,
    restrict_form_fields,
)
from nautobot.utilities.permissions import resolve_permission
from nautobot.core.views.renderers import NautobotHTMLRenderer
from nautobot.utilities.utils import (
    csv_format,
    prepare_cloned_fields,
)
from nautobot.utilities.views import GetReturnURLMixin

PERMISSIONS_ACTION_MAP = {
    "list": "view",
    "retrieve": "view",
    "destroy": "delete",
    "create": "add",
    "update": "change",
    "bulk_create": "add",
    "bulk_destroy": "delete",
    "bulk_update": "change",
}


class NautobotViewSetMixin(ViewSetMixin, generics.GenericAPIView, AccessMixin, GetReturnURLMixin, FormView):
    """
    serializer_class has to be specified to eliminate the need to override retrieve() in the RetrieveModelMixin for now.
    It is a step forward in our transition from NetBox legacy code to DRF framework.
    NautobotHTMLRenderer is inherited from BrowsableAPIRenderer to render the original context needed for rendering the templates.
    """

    serializer_class = None
    renderer_classes = [NautobotHTMLRenderer]

    def get_permissions_for_model(self, model, actions):
        """
        Resolve the named permissions for a given model (or instance) and a list of actions (e.g. view or add).

        :param model: A model or instance
        :param actions: A list of actions to perform on the model
        """
        permissions = []
        for action in actions:
            if action not in ("view", "add", "change", "delete"):
                raise ValueError(f"Unsupported action: {action}")
        permissions.append("{}.{}_{}".format(model._meta.app_label, action, model._meta.model_name))
        return permissions

    def get_required_permission(self):
        """
        Obtain the permissions needed to perform certain actions on a model.
        """
        return self.get_permissions_for_model(self.queryset.model, [PERMISSIONS_ACTION_MAP[self.action]])

    def has_permission(self):
        """
        Check whether the user has the permissions needed to perform certain actions.
        """
        user = self.request.user
        permission_required = self.get_required_permission()
        # Check that the user has been granted the required permission(s).
        if user.has_perms(permission_required):

            # Update the view's QuerySet to filter only the permitted objects
            for permission in permission_required:
                action = resolve_permission(permission)[1]
                self.queryset = self.queryset.restrict(user, action)

            return True

        return False

    def check_permissions(self, request):
        """
        Used to determine whether the user has permissions to a view.
        Using AccessMixin handle_no_permission() to deal with Object-Level permissions and API-Level permissions in one pass.
        """
        if not self.has_permission():
            self.handle_no_permission()

    def check_object_permissions(self, request, obj):
        """
        Used to determine whether the user has the object-level permissions to perform certain actions to a model instance.
        Using AccessMixin handle_no_permission() to deal with Object-Level permissions and API-Level permissions in one pass.
        """
        if not self.has_permission():
            self.handle_no_permission()

    def _process_destroy_form(self, form):
        """
        Helper method to destroy an object after the form is validated successfully.
        """
        raise NotImplementedError("_process_destroy_form() is not implemented")

    def _process_bulk_destroy_form(self, form):
        """
        Helper method to destroy objects after the form is validated successfully.
        """
        raise NotImplementedError("_process_bulk_destroy_form() is not implemented")

    def _process_create_or_update_form(self, form):
        """
        Helper method to create or update an object after the form is validated successfully.
        """
        raise NotImplementedError("_process_create_or_update_form() is not implemented")

    def _process_bulk_update_form(self, form):
        """
        Helper method to edit objects in bulk after the form is validated successfully.
        """
        raise NotImplementedError("_process_bulk_update_form() is not implemented")

    def _process_bulk_create_form(self, form):
        """
        Helper method to create objects in bulk after the form is validated successfully.
        """
        raise NotImplementedError("_process_bulk_create_form() is not implemented")

    def _handle_object_does_not_exist(self, form, logger):
        msg = "Object import failed due to object-level permissions violation"
        logger.debug(msg)
        self.has_error = True
        form.add_error(None, msg)
        return form

    def alter_queryset(self, request):
        # .all() is necessary to avoid caching queries
        return self.queryset.all()

    def alter_obj_for_edit(self, obj, request, url_args, url_kwargs):
        # Allow views to add extra info to an object before it is processed. For example, a parent object can be defined
        # given some parameter from the request URL.
        return obj

    def form_valid(self, form):
        """
        Handle valid forms and redirect to success_url.
        """
        request = self.request
        self.has_error = False
        if self.action == "destroy":
            logger = logging.getLogger("nautobot.views.ObjectDestroyView")
            self._process_destroy_form(form)
        elif self.action == "bulk_destroy":
            logger = logging.getLogger("nautobot.views.BulkDestroyView")
            self._process_bulk_destroy_form(form)
        elif self.action in ["create", "update"]:
            logger = logging.getLogger("nautobot.views.ObjectEditView")
            try:
                self._process_create_or_update_form(form)
            except ObjectDoesNotExist:
                form = self._handle_object_does_not_exist(form, logger)
        elif self.action == "bulk_update":
            logger = logging.getLogger("nautobot.views.BulkUpdateView")
            try:
                self._process_bulk_update_form(form)
            except ValidationError as e:
                messages.error(self.request, f"{self.obj} failed validation: {e}")
                self.has_error = True
            except ObjectDoesNotExist:
                form = self._handle_object_does_not_exist(form, logger)
        elif self.action == "bulk_create":
            logger = logging.getLogger("nautobot.views.BulkCreateView")
            try:
                self.obj_table = self._process_bulk_create_form(form)
            except ValidationError:
                self.has_error = True
                pass
            except ObjectDoesNotExist:
                form = self._handle_object_does_not_exist(form, logger)

        if not self.has_error:
            logger.debug("Form validation was successful")
            if self.action == "bulk_create":
                return Response(
                    {
                        "table": self.obj_table,
                        "template": "import_success.html",
                    }
                )
            return super().form_valid(form)
        else:
            data = {}
            if self.action in ["bulk_update", "bulk_destroy"]:
                pk_list = self.request.POST.getlist("pk")
                table = self.table_class(self.queryset.filter(pk__in=pk_list), orderable=False)
                if not table.rows:
                    messages.warning(
                        request,
                        f"No {self.queryset.model._meta.verbose_name_plural} were selected for {self.action}.",
                    )
                    return redirect(self.get_return_url(request))

                data.update({"table": table})
            data.update({"form": form})
            return Response(data)

    def form_invalid(self, form):
        """
        Handle invalid forms.
        """
        data = {}
        request = self.request
        if self.action in ["bulk_update", "bulk_destroy"]:
            pk_list = self.request.POST.getlist("pk")
            table = self.table_class(self.queryset.filter(pk__in=pk_list), orderable=False)
            if not table.rows:
                messages.warning(
                    request,
                    f"No {self.queryset.model._meta.verbose_name_plural} were selected for {self.action}.",
                )
                return redirect(self.get_return_url(request))

            data = {
                "table": table,
            }
        data.update({"form": form})
        return Response(data)

    def get_object(self):
        """
        Returns the object the view is displaying.
        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        queryset = self.queryset
        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if lookup_url_kwarg not in self.kwargs:
            return self.queryset.model()
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_extra_context(self, request, instance=None):
        """
        Return any additional context data for the template.
        request: The current request
        instance: The object being viewed
        """
        return {}

    def get_template_name(self):
        # Use "<app>/<model>_<action> if available, else fall back to generic templates
        model_opts = self.model._meta
        app_label = model_opts.app_label
        action = self.action
        if action in ["create", "update"]:
            action = "create_or_update"
        try:
            select_template([f"{app_label}/{model_opts.model_name}_{action}.html"])
            return f"{app_label}/{model_opts.model_name}_{action}.html"
        except TemplateDoesNotExist:
            return f"generic/object_{action}.html"

    def get_form(self, *args, **kwargs):
        """
        Helper function to get form for different views if specified.
        If not, return instantiated form using form_class.
        """
        form = getattr(self, f"{self.action}_form", None)
        if not form:
            if self.action == "bulk_create":

                class BulkCreateForm(BootstrapMixin, Form):
                    csv_data = CSVDataField(
                        from_form=self.bulk_create_form_class, widget=Textarea(attrs=self.bulk_create_widget_attrs)
                    )
                    csv_file = CSVFileField(from_form=self.bulk_create_form_class)

                return BulkCreateForm(*args, **kwargs)
            else:
                form_class = self.get_form_class()
                form = form_class(*args, **kwargs)
        return form

    def get_form_class(self, **kwargs):
        """
        Helper function to get form_class for different views.
        """
        if self.action in ["create", "update"]:
            form_class = getattr(self, "form_class", None)
        else:
            form_class = getattr(self, f"{self.action}_form_class", None)
        if not form_class:
            if self.action == "bulk_destroy":

                class BulkDestroyForm(ConfirmationForm):
                    pk = ModelMultipleChoiceField(queryset=self.queryset, widget=MultipleHiddenInput)

                return BulkDestroyForm
            else:
                form_class = kwargs.get("form_class", None)
        return form_class

    def form_save(self, form, **kwargs):
        """
        Generic method to save the object from form.
        Should be overriden by user if customization is needed.
        """
        return form.save()


class ObjectDetailViewMixin(NautobotViewSetMixin, mixins.RetrieveModelMixin):
    def get_changelog_url(self, instance):
        """Return the changelog URL for a given instance."""
        meta = self.queryset.model._meta

        # Don't try to generate a changelog_url for an ObjectChange.
        if not issubclass(self.queryset.model, ChangeLoggedModel):
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


class ObjectListViewMixin(NautobotViewSetMixin, mixins.ListModelMixin):
    action_buttons = ("add", "import", "export")
    filterset_class = None
    filterset_form_class = None
    non_filter_params = (
        "export",  # trigger for CSV/export-template/YAML export
        "page",  # used by django-tables2.RequestConfig
        "per_page",  # used by get_paginate_count
        "sort",  # table sorting
    )

    def check_for_export(self, request, model, content_type):
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
                    f"There was an error rendering the selected export template ({et.name}): {e}",
                )

        # Check for YAML export support
        elif "export" in request.GET and hasattr(model, "to_yaml"):
            response = HttpResponse(self.queryset_to_yaml(), content_type="text/yaml")
            filename = f"nautobot_{self.queryset.model._meta.verbose_name_plural}.yaml"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        # Fall back to built-in CSV formatting if export requested but no template specified
        elif "export" in request.GET and hasattr(model, "to_csv"):
            response = HttpResponse(self.queryset_to_csv(), content_type="text/csv")
            filename = f"nautobot_{self.queryset.model._meta.verbose_name_plural}.csv"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

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

    def list(self, request, *args, **kwargs):
        """
        List the model instances.
        """
        context = {}
        if "export" in request.GET:
            model = self.model
            content_type = ContentType.objects.get_for_model(model)
            return self.check_for_export(request, model, content_type)
        return Response(context)


class ObjectDestroyViewMixin(NautobotViewSetMixin, mixins.DestroyModelMixin):
    destroy_form_class = ConfirmationForm

    def _process_destroy_form(self, form):
        request = self.request
        obj = self.obj
        logger = logging.getLogger("nautobot.views.ObjectDestroyView")
        try:
            with transaction.atomic():
                obj.delete()
                msg = f"Deleted {self.model._meta.verbose_name} {obj}"
                logger.info(msg)
                messages.success(request, msg)
                self.success_url = self.get_return_url(request)
        except ProtectedError as e:
            logger.info("Caught ProtectedError while attempting to delete object")
            handle_protectederror([obj], request, e)
            self.success_url = obj.get_absolute_url()

    def destroy(self, request, *args, **kwargs):
        """
        request.GET: render the ObjectDeleteConfirmationForm which is passed to NautobotHTMLRenderer as Response.
        request.POST: call perform_destroy() which validates the form and perform the action of delete.
        Override to add more variables to Response
        """
        context = {}
        if request.method == "POST":
            return self.perform_destroy(request, **kwargs)
        return Response(context)

    def perform_destroy(self, request, **kwargs):
        """
        Function to validate the ObjectDeleteConfirmationForm and to delete the object.
        """
        self.obj = self.get_object()
        form_class = self.get_form_class()
        form = form_class(request.POST)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ObjectEditViewMixin(NautobotViewSetMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin):
    def _process_create_or_update_form(self, form):
        """
        Helper method to create or update an object after the form is validated successfully.
        """
        request = self.request
        logger = logging.getLogger("nautobot.views.ObjectEditView")
        with transaction.atomic():
            object_created = not form.instance.present_in_database
            obj = self.form_save(form)

            # Check that the new object conforms with any assigned object-level permissions
            self.queryset.get(pk=obj.pk)
            msg = f'{"Created" if object_created else "Modified"} {self.queryset.model._meta.verbose_name}'
            logger.info(f"{msg} {obj} (PK: {obj.pk})")
            if hasattr(obj, "get_absolute_url"):
                msg = f'{msg} <a href="{obj.get_absolute_url()}">{escape(obj)}</a>'
            else:
                msg = f"{msg} { escape(obj)}"
            messages.success(request, mark_safe(msg))
            if "_addanother" in request.POST:
                # If the object has clone_fields, pre-populate a new instance of the form
                if hasattr(obj, "clone_fields"):
                    url = f"{request.path}?{prepare_cloned_fields(obj)}"
                    self.success_url = url
                self.success_url = request.get_full_path()
            else:
                return_url = form.cleaned_data.get("return_url")
                if return_url is not None and is_safe_url(url=return_url, allowed_hosts=request.get_host()):
                    self.success_url = return_url
                else:
                    self.success_url = self.get_return_url(request, obj)

    def create(self, request, *args, **kwargs):
        """
        request.GET: render the ObjectForm which is passed to NautobotHTMLRenderer as Response.
        request.POST: call perform_create() which validates the form and perform the action of create.
        Override to add more variables to Response.
        """
        context = {}
        if request.method == "POST":
            return self.perform_create(request, *args, **kwargs)
        return Response(context)

    def perform_create(self, request, *args, **kwargs):
        """
        Function to validate the ObjectForm and to create a new object.
        """
        self.obj = self.alter_obj_for_edit(self.get_object(), request, args, kwargs)
        form_class = self.get_form_class()
        form = form_class(data=request.POST, files=request.FILES, instance=self.obj)
        restrict_form_fields(form, request.user)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def update(self, request, *args, **kwargs):
        """
        request.GET: render the ObjectEditForm which is passed to NautobotHTMLRenderer as Response.
        request.POST: call perform_update() which validates the form and perform the action of update/partial_update of an existing object.
        Override to add more variables to Response.
        """
        context = {}
        if request.method == "POST":
            return self.perform_update(request, *args, **kwargs)
        return Response(context)

    def perform_update(self, request, *args, **kwargs):
        """
        Function to validate the ObjectEditForm and to update/partial_update an existing object.
        """
        self.obj = self.alter_obj_for_edit(self.get_object(), request, args, kwargs)
        form_class = self.get_form_class()
        form = form_class(data=request.POST, files=request.FILES, instance=self.obj)
        restrict_form_fields(form, request.user)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class BulkDestroyViewMixin(NautobotViewSetMixin, bulk_mixins.BulkDestroyModelMixin):
    bulk_destroy_form_class = None
    filterset_class = None

    def _process_bulk_destroy_form(self, form):
        request = self.request
        pk_list = self.request.POST.getlist("pk")
        model = self.model
        # Delete objects
        queryset = self.queryset.filter(pk__in=pk_list)
        logger = logging.getLogger("nautobot.views.BulkDestroyView")

        try:
            with transaction.atomic():
                deleted_count = queryset.delete()[1][model._meta.label]
                msg = f"Deleted {deleted_count} {model._meta.verbose_name_plural}"
                logger.info(msg)
                self.success_url = self.get_return_url(request)
                messages.success(request, msg)
        except ProtectedError as e:
            logger.info("Caught ProtectedError while attempting to delete objects")
            handle_protectederror(queryset, request, e)
            self.success_url = self.get_return_url(request)

    def bulk_destroy(self, request, *args, **kwargs):
        """
        Call perform_bulk_destroy().
        The function exist to keep the DRF's get/post pattern of {action}/perform_{action}, we will need it when we transition from using forms to serializers in the UI.
        User should override this function to handle any actions as needed before bulk destroy.
        """
        return self.perform_bulk_destroy(request, **kwargs)

    def perform_bulk_destroy(self, request, **kwargs):
        """
        request.POST "_delete": Function to render the user selection of objects in a table form/BulkDestroyConfirmationForm via Response that is passed to NautobotHTMLRenderer.
        request.POST "_confirm": Function to validate the table form/BulkDestroyConfirmationForm and to perform the action of bulk destroy. Render the form with errors if exceptions are raised.
        """
        model = self.model
        # Are we deleting *all* objects in the queryset or just a selected subset?
        if request.POST.get("_all"):
            if self.filterset_class is not None:
                self.pk_list = [obj.pk for obj in self.filterset_class(request.GET, model.objects.only("pk")).qs]
            else:
                self.pk_list = model.objects.values_list("pk", flat=True)
        else:
            self.pk_list = request.POST.getlist("pk")
        form_class = self.get_form_class(**kwargs)
        data = {}
        if "_confirm" in request.POST:
            form = form_class(request.POST)
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        table = self.table_class(self.queryset.filter(pk__in=self.pk_list), orderable=False)
        if not table.rows:
            messages.warning(
                request,
                f"No {self.queryset.model._meta.verbose_name_plural} were selected for deletion.",
            )
            return redirect(self.get_return_url(request))

        data.update({"table": table})
        return Response(data)


class BulkCreateViewMixin(NautobotViewSetMixin, bulk_mixins.BulkCreateModelMixin):
    bulk_create_form_class = None
    bulk_create_widget_attrs = {}

    def _process_bulk_create_form(self, form):
        # Iterate through CSV data and bind each row to a new model form instance.
        new_objs = []
        request = self.request
        logger = logging.getLogger("nautobot.views.BulkCreateView")
        with transaction.atomic():
            if request.FILES:
                field_name = "csv_file"
            else:
                field_name = "csv_data"
            headers, records = form.cleaned_data[field_name]
            for row, data in enumerate(records, start=1):
                form_class = self.get_form_class()
                obj_form = form_class(data, headers=headers)
                restrict_form_fields(obj_form, request.user)

                if obj_form.is_valid():
                    obj = self.form_save(obj_form)
                    new_objs.append(obj)
                else:
                    for field, err in obj_form.errors.items():
                        form.add_error("csv_data", f"Row {row} {field}: {err[0]}")
                    raise ValidationError("")

            # Enforce object-level permissions
            if self.queryset.filter(pk__in=[obj.pk for obj in new_objs]).count() != len(new_objs):
                raise ObjectDoesNotExist

        # Compile a table containing the imported objects
        obj_table = self.table_class(new_objs)
        if new_objs:
            msg = f"Imported {len(new_objs)} {new_objs[0]._meta.verbose_name_plural}"
            logger.info(msg)
            messages.success(request, msg)
        return obj_table

    def bulk_create(self, request):
        context = {}
        if request.method == "POST":
            return self.perform_bulk_create(request)
        return Response(context)

    def perform_bulk_create(self, request):
        form = self.get_form(request.POST)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class BulkUpdateViewMixin(NautobotViewSetMixin, bulk_mixins.BulkUpdateModelMixin):
    filterset_class = None
    bulk_update_form_class = None

    def _process_bulk_update_form(self, form):
        request = self.request
        model = self.model
        form_custom_fields = getattr(form, "custom_fields", [])
        form_relationships = getattr(form, "relationships", [])
        standard_fields = [
            field for field in form.fields if field not in form_custom_fields + form_relationships + ["pk"]
        ]
        nullified_fields = request.POST.getlist("_nullify")
        form_cf_to_key = {f"cf_{cf.slug}": cf.name for cf in CustomField.objects.get_for_model(model)}
        logger = logging.getLogger("nautobot.views.BulkUpdateView")
        with transaction.atomic():
            updated_objects = []
            for obj in self.queryset.filter(pk__in=form.cleaned_data["pk"]):
                self.obj = obj
                obj = self.alter_obj_for_bulk_update(obj, request, [], self.kwargs)
                # Update standard fields. If a field is listed in _nullify, delete its value.
                for name in standard_fields:
                    try:
                        model_field = model._meta.get_field(name)
                    except FieldDoesNotExist:
                        # This form field is used to modify a field rather than set its value directly
                        model_field = None
                    # Handle nullification
                    if name in form.nullable_fields and name in nullified_fields:
                        if isinstance(model_field, ManyToManyField):
                            getattr(obj, name).set([])
                        else:
                            setattr(obj, name, None if model_field is not None and model_field.null else "")
                    # ManyToManyFields
                    elif isinstance(model_field, ManyToManyField):
                        if form.cleaned_data[name]:
                            getattr(obj, name).set(form.cleaned_data[name])
                    # Normal fields
                    elif form.cleaned_data[name] not in (None, ""):
                        setattr(obj, name, form.cleaned_data[name])
                # Update custom fields
                for field_name in form_custom_fields:
                    if field_name in form.nullable_fields and field_name in nullified_fields:
                        obj.cf[form_cf_to_key[field_name]] = None
                    elif form.cleaned_data.get(field_name) not in (None, ""):
                        obj.cf[form_cf_to_key[field_name]] = form.cleaned_data[field_name]

                obj.full_clean()
                obj.save()
                updated_objects.append(obj)
                logger.debug(f"Saved {obj} (PK: {obj.pk})")

                # Add/remove tags
                if form.cleaned_data.get("add_tags", None):
                    obj.tags.add(*form.cleaned_data["add_tags"])
                if form.cleaned_data.get("remove_tags", None):
                    obj.tags.remove(*form.cleaned_data["remove_tags"])

                if hasattr(form, "save_relationships") and callable(form.save_relationships):
                    # Add/remove relationship associations
                    form.save_relationships(instance=obj, nullified_fields=nullified_fields)

            # Enforce object-level permissions
            if self.queryset.filter(pk__in=[obj.pk for obj in updated_objects]).count() != len(updated_objects):
                raise ObjectDoesNotExist
        if updated_objects:
            msg = f"Updated {len(updated_objects)} {model._meta.verbose_name_plural}"
            logger.info(msg)
            messages.success(self.request, msg)
        self.success_url = self.get_return_url(request)

    def alter_obj_for_bulk_update(self, obj, request, url_args, url_kwargs):
        # Allow views to add extra info to an object before it is processed.
        # For example, a parent object can be defined given some parameter from the request URL.
        return obj

    def bulk_update(self, request, *args, **kwargs):
        """
        Call perform_bulk_update().
        The function exist to keep the DRF's get/post pattern of {action}/perform_{action}, we will need it when we transition from using forms to serializers in the UI.
        User should override this function to handle any actions as needed before bulk update.
        """
        print(request.POST)
        return self.perform_bulk_update(request, **kwargs)

    def perform_bulk_update(self, request, **kwargs):
        """
        request.POST "_edit": Function to render the user selection of objects in a table form/BulkUpdateForm via Response that is passed to NautobotHTMLRenderer.
        request.POST "_apply": Function to validate the table form/BulkUpdateForm and to perform the action of bulk update. Render the form with errors if exceptions are raised.
        """
        model = self.model

        # If we are editing *all* objects in the queryset, replace the PK list with all matched objects.
        if request.POST.get("_all") and self.filterset_class is not None:
            self.pk_list = [obj.pk for obj in self.filterset_class(request.GET, self.queryset.only("pk")).qs]
        else:
            self.pk_list = request.POST.getlist("pk")
        data = {}
        form_class = self.get_form_class()
        if "_apply" in request.POST:
            self.kwargs = kwargs
            form = form_class(model, request.POST)
            restrict_form_fields(form, request.user)
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)

        table = self.table_class(self.queryset.filter(pk__in=self.pk_list), orderable=False)
        if not table.rows:
            messages.warning(
                request,
                f"No {self.queryset.model._meta.verbose_name_plural} were selected for deletion.",
            )
            return redirect(self.get_return_url(request))
        data.update({"table": table})
        return Response(data)


class NautobotDRFViewSet(
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectEditViewMixin,
    ObjectDestroyViewMixin,
    BulkDestroyViewMixin,
    BulkCreateViewMixin,
    BulkUpdateViewMixin,
):
    """
    This is the UI BaseViewSet you should inherit.
    """
