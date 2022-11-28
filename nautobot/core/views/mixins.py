import logging

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
from django.utils.http import is_safe_url
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormView

from rest_framework import mixins, exceptions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from drf_spectacular.utils import extend_schema

from nautobot.core.api.views import BulkCreateModelMixin, BulkDestroyModelMixin, BulkUpdateModelMixin
from nautobot.extras.models import CustomField, ExportTemplate
from nautobot.utilities.error_handlers import handle_protectederror
from nautobot.utilities.forms import (
    BootstrapMixin,
    ConfirmationForm,
    CSVDataField,
    CSVFileField,
    restrict_form_fields,
)
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


@extend_schema(exclude=True)
class NautobotViewSetMixin(GenericViewSet, AccessMixin, GetReturnURLMixin, FormView):
    """
    NautobotViewSetMixin is an aggregation of various mixins from DRF, Django and Nautobot to acheive the desired behavior pattern for NautobotUIViewSet
    """

    renderer_classes = [NautobotHTMLRenderer]
    logger = logging.getLogger(__name__)
    lookup_field = "slug"
    # Attributes that need to be specified: form_class, queryset, serializer_class, table_class for most mixins.
    filterset_class = None
    filterset_form_class = None
    form_class = None
    queryset = None
    # serializer_class has to be specified to eliminate the need to override retrieve() in the RetrieveModelMixin for now.
    serializer_class = None
    table_class = None

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
            permissions.append(f"{model._meta.app_label}.{action}_{model._meta.model_name}")
        return permissions

    def get_required_permission(self):
        """
        Obtain the permissions needed to perform certain actions on a model.
        """
        queryset = self.get_queryset()
        try:
            permissions = [PERMISSIONS_ACTION_MAP[self.action]]
        except KeyError:
            messages.error(
                self.request,
                "This action is not permitted. Please use the buttons at the bottom of the table for Bulk Delete and Bulk Update",
            )
        return self.get_permissions_for_model(queryset.model, permissions)

    def check_permissions(self, request):
        """
        Check whether the user has the permissions needed to perform certain actions.
        """
        user = self.request.user
        permission_required = self.get_required_permission()
        # Check that the user has been granted the required permission(s) one by one.
        # In case the permission has `message` or `code`` attribute, we want to include those information in the permission_denied error.
        for permission in permission_required:
            # If the user does not have the permission required, we raise DRF's `NotAuthenticated` or `PermissionDenied` exception
            # which will be handled by self.handle_no_permission() in the UI appropriately in the dispatch() method
            # Cast permission to a list since has_perms() takes a list type parameter.
            if not user.has_perms([permission]):
                self.permission_denied(
                    request,
                    message=getattr(permission, "message", None),
                    code=getattr(permission, "code", None),
                )

    def dispatch(self, request, *args, **kwargs):
        """
        Override the default dispatch() method to check permissions first.
        Used to determine whether the user has permissions to a view and object-level permissions.
        Using AccessMixin handle_no_permission() to deal with Object-Level permissions and API-Level permissions in one pass.
        """
        # self.initialize_request() converts a WSGI request and returns an API request object which can be passed into self.check_permissions()
        # If the user is not authenticated or does not have the permission to perform certain actions,
        # DRF NotAuthenticated or PermissionDenied exception can be raised appropriately and handled by self.handle_no_permission() in the UI.
        # initialize_request() also instantiates self.action which is needed for permission checks.
        api_request = self.initialize_request(request, *args, **kwargs)
        try:
            self.check_permissions(api_request)
        # check_permissions() could raise NotAuthenticated and PermissionDenied Error.
        # We handle them by a single except statement since self.handle_no_permission() is able to handle both errors
        except (exceptions.NotAuthenticated, exceptions.PermissionDenied):
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def get_table_class(self):
        # Check if self.table_class is specified in the ModelViewSet before performing subsequent actions
        # If not, display an error message
        assert (
            self.table_class is not None
        ), f"'{self.__class__.__name__}' should include a `table_class` attribute for bulk operations"

        return self.table_class

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

    def _handle_object_does_not_exist(self, form):
        msg = "Object import failed due to object-level permissions violation"
        self.logger.debug(msg)
        self.has_error = True
        form.add_error(None, msg)
        return form

    def _handle_not_implemented_error(self):
        # Blanket handler for NotImplementedError raised by form helper functions
        msg = "Please provide the appropriate mixin before using this helper function"
        messages.error(self.request, msg)
        self.has_error = True

    def _handle_validation_error(self, e):
        # For bulk_create/bulk_update view, self.obj is not set since there are multiple
        # The errors will be rendered on the form itself.
        if self.action not in ["bulk_create", "bulk_update"]:
            messages.error(self.request, f"{self.obj} failed validation: {e}")
        self.has_error = True

    def form_valid(self, form):
        """
        Handle valid forms and redirect to success_url.
        """
        request = self.request
        self.has_error = False
        queryset = self.get_queryset()
        try:
            if self.action == "destroy":
                self._process_destroy_form(form)
            elif self.action == "bulk_destroy":
                self._process_bulk_destroy_form(form)
            elif self.action in ["create", "update"]:
                self._process_create_or_update_form(form)
            elif self.action == "bulk_update":
                self._process_bulk_update_form(form)
            elif self.action == "bulk_create":
                self.obj_table = self._process_bulk_create_form(form)
        except ValidationError as e:
            self._handle_validation_error(e)
        except ObjectDoesNotExist:
            form = self._handle_object_does_not_exist(form)
        except NotImplementedError:
            self._handle_not_implemented_error()

        if not self.has_error:
            self.logger.debug("Form validation was successful")
            if self.action == "bulk_create":
                return Response(
                    {
                        "table": self.obj_table,
                        "template": "import_success.html",
                    }
                )
            return super().form_valid(form)
        else:
            # render the form with the error message.
            data = {}
            if self.action in ["bulk_update", "bulk_destroy"]:
                pk_list = self.pk_list
                table_class = self.get_table_class()
                table = table_class(queryset.filter(pk__in=pk_list), orderable=False)
                if not table.rows:
                    messages.warning(
                        request,
                        f"No {queryset.model._meta.verbose_name_plural} were selected for {self.action}.",
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
        queryset = self.get_queryset()
        if self.action in ["bulk_update", "bulk_destroy"]:
            pk_list = self.pk_list
            table_class = self.get_table_class()
            table = table_class(queryset.filter(pk__in=pk_list), orderable=False)
            if not table.rows:
                messages.warning(
                    request,
                    f"No {queryset.model._meta.verbose_name_plural} were selected for {self.action}.",
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
        queryset = self.get_queryset()
        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if lookup_url_kwarg not in self.kwargs:
            return queryset.model()
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        return obj

    def get_queryset(self):
        """
        Get the list of items for this view.
        This must be an iterable, and may be a queryset.
        Defaults to using `self.queryset`.
        This method should always be used rather than accessing `self.queryset`
        directly, as `self.queryset` gets evaluated only once, and those results
        are cached for all subsequent requests.
        Override the original `get_queryset()` to apply permission specific to the user and action.
        """
        queryset = super().get_queryset()
        return queryset.restrict(self.request.user, PERMISSIONS_ACTION_MAP[self.action])

    def get_extra_context(self, request, instance=None):
        """
        Return any additional context data for the template.
        request: The current request
        instance: The object being viewed
        """
        return {}

    def get_template_name(self):
        # Use "<app>/<model>_<action> if available, else fall back to generic templates
        queryset = self.get_queryset()
        model_opts = queryset.model._meta
        app_label = model_opts.app_label
        action = self.action

        try:
            template_name = f"{app_label}/{model_opts.model_name}_{action}.html"
            select_template([template_name])
        except TemplateDoesNotExist:
            try:
                if action == "create":
                    # When the action is `create`, try {object}_update.html as a fallback
                    # If both are not defined, fall back to generic/object_create.html
                    template_name = f"{app_label}/{model_opts.model_name}_update.html"
                    select_template([template_name])
                elif action == "update":
                    # When the action is `update`, try {object}_create.html as a fallback
                    # If both are not defined, fall back to generic/object_update.html
                    template_name = f"{app_label}/{model_opts.model_name}_create.html"
                    select_template([template_name])
                else:
                    # No special case fallback, fall back to generic/object_{action}.html
                    raise TemplateDoesNotExist("")
            except TemplateDoesNotExist:
                template_name = f"generic/object_{action}.html"
        return template_name

    def get_form(self, *args, **kwargs):
        """
        Helper function to get form for different views if specified.
        If not, return instantiated form using form_class.
        """
        form = getattr(self, f"{self.action}_form", None)
        if not form:
            form_class = self.get_form_class()
            if not form_class:
                self.logger.debug(f"{self.action}_form_class is not defined")
                return None
            form = form_class(*args, **kwargs)
        return form

    def get_form_class(self, **kwargs):
        """
        Helper function to get form_class for different views.
        """

        if self.action in ["create", "update"]:
            form_class = getattr(self, "form_class", None)
        elif self.action == "bulk_create":

            class BulkCreateForm(BootstrapMixin, Form):
                csv_data = CSVDataField(
                    from_form=self.bulk_create_form_class, widget=Textarea(attrs=self.bulk_create_widget_attrs)
                )
                csv_file = CSVFileField(from_form=self.bulk_create_form_class)

            form_class = BulkCreateForm
        else:
            form_class = getattr(self, f"{self.action}_form_class", None)

        if not form_class:
            if self.action == "bulk_destroy":
                queryset = self.get_queryset()

                class BulkDestroyForm(ConfirmationForm):
                    pk = ModelMultipleChoiceField(queryset=queryset, widget=MultipleHiddenInput)

                return BulkDestroyForm
            else:
                # Check for request first and then kwargs for form_class specified.
                form_class = self.request.data.get("form_class", None)
                if not form_class:
                    form_class = kwargs.get("form_class", None)
        return form_class

    def form_save(self, form, **kwargs):
        """
        Generic method to save the object from form.
        Should be overriden by user if customization is needed.
        """
        return form.save()

    def alter_queryset(self, request):
        # .all() is necessary to avoid caching queries
        queryset = self.get_queryset()
        return queryset.all()


class ObjectDetailViewMixin(NautobotViewSetMixin, mixins.RetrieveModelMixin):
    """
    UI mixin to retrieve a model instance.
    """


class ObjectListViewMixin(NautobotViewSetMixin, mixins.ListModelMixin):
    """
    UI mixin to list a model queryset
    """

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
        queryset = self.get_queryset()
        if request.GET.get("export"):
            et = get_object_or_404(
                ExportTemplate,
                content_type=content_type,
                name=request.GET.get("export"),
            )
            try:
                return et.render_to_response(queryset)
            except Exception as e:
                messages.error(
                    request,
                    f"There was an error rendering the selected export template ({et.name}): {e}",
                )

        # Check for YAML export support
        elif "export" in request.GET and hasattr(model, "to_yaml"):
            response = HttpResponse(self.queryset_to_yaml(), content_type="text/yaml")
            filename = f"nautobot_{queryset.model._meta.verbose_name_plural}.yaml"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        # Fall back to built-in CSV formatting if export requested but no template specified
        elif "export" in request.GET and hasattr(model, "to_csv"):
            response = HttpResponse(self.queryset_to_csv(), content_type="text/csv")
            filename = f"nautobot_{queryset.model._meta.verbose_name_plural}.csv"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        return None

    def queryset_to_yaml(self):
        """
        Export the queryset of objects as concatenated YAML documents.
        """
        queryset = self.get_queryset()
        yaml_data = [obj.to_yaml() for obj in queryset]

        return "---\n".join(yaml_data)

    def queryset_to_csv(self):
        """
        Export the queryset of objects as comma-separated value (CSV), using the model's to_csv() method.
        """
        queryset = self.get_queryset()
        csv_data = []
        custom_fields = []
        # Start with the column headers
        headers = queryset.model.csv_headers.copy()

        # Add custom field headers, if any
        if hasattr(queryset.model, "_custom_field_data"):
            for custom_field in CustomField.objects.get_for_model(queryset.model):
                headers.append("cf_" + custom_field.slug)
                custom_fields.append(custom_field.name)

        csv_data.append(",".join(headers))

        # Iterate through the queryset appending each object
        for obj in queryset:
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
            queryset = self.get_queryset()
            model = queryset.model
            content_type = ContentType.objects.get_for_model(model)
            response = self.check_for_export(request, model, content_type)
            if response is not None:
                return response
        return Response(context)


class ObjectDestroyViewMixin(NautobotViewSetMixin, mixins.DestroyModelMixin):
    """
    UI mixin to destroy a model instance.
    """

    destroy_form_class = ConfirmationForm

    def _process_destroy_form(self, form):
        request = self.request
        obj = self.obj
        queryset = self.get_queryset()
        try:
            with transaction.atomic():
                obj.delete()
                msg = f"Deleted {queryset.model._meta.verbose_name} {obj}"
                self.logger.info(msg)
                messages.success(request, msg)
                self.success_url = self.get_return_url(request, obj)
        except ProtectedError as e:
            self.logger.info("Caught ProtectedError while attempting to delete object")
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
    """
    UI mixin to create or update a model instance.
    """

    def _process_create_or_update_form(self, form):
        """
        Helper method to create or update an object after the form is validated successfully.
        """
        request = self.request
        queryset = self.get_queryset()
        with transaction.atomic():
            object_created = not form.instance.present_in_database
            obj = self.form_save(form)

            # Check that the new object conforms with any assigned object-level permissions
            queryset.get(pk=obj.pk)

            if hasattr(form, "save_note") and callable(form.save_note):
                form.save_note(instance=obj, user=request.user)

            msg = f'{"Created" if object_created else "Modified"} {queryset.model._meta.verbose_name}'
            self.logger.info(f"{msg} {obj} (PK: {obj.pk})")
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

    # TODO: this conflicts with DRF's CreateModelMixin.perform_create(self, serializer) API
    def perform_create(self, request, *args, **kwargs):  # pylint: disable=arguments-differ
        """
        Function to validate the ObjectForm and to create a new object.
        """
        self.obj = self.get_object()
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

    # TODO: this conflicts with DRF's UpdateModelMixin.perform_update(self, serializer) API
    def perform_update(self, request, *args, **kwargs):  # pylint: disable=arguments-differ
        """
        Function to validate the ObjectEditForm and to update/partial_update an existing object.
        """
        self.obj = self.get_object()
        form_class = self.get_form_class()
        form = form_class(data=request.POST, files=request.FILES, instance=self.obj)
        restrict_form_fields(form, request.user)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ObjectBulkDestroyViewMixin(NautobotViewSetMixin, BulkDestroyModelMixin):
    """
    UI mixin to bulk destroy model instances.
    """

    bulk_destroy_form_class = None
    filterset_class = None

    def _process_bulk_destroy_form(self, form):
        request = self.request
        pk_list = self.pk_list
        queryset = self.get_queryset()
        model = queryset.model
        # Delete objects
        queryset = queryset.filter(pk__in=pk_list)

        try:
            with transaction.atomic():
                deleted_count = queryset.delete()[1][model._meta.label]
                msg = f"Deleted {deleted_count} {model._meta.verbose_name_plural}"
                self.logger.info(msg)
                self.success_url = self.get_return_url(request)
                messages.success(request, msg)
        except ProtectedError as e:
            self.logger.info("Caught ProtectedError while attempting to delete objects")
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
        queryset = self.get_queryset()
        model = queryset.model
        # Are we deleting *all* objects in the queryset or just a selected subset?
        if request.POST.get("_all"):
            if self.filterset_class is not None:
                self.pk_list = [obj.pk for obj in self.filterset_class(request.POST, model.objects.only("pk")).qs]
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
        table_class = self.get_table_class()
        table = table_class(queryset.filter(pk__in=self.pk_list), orderable=False)
        if not table.rows:
            messages.warning(
                request,
                f"No {queryset.model._meta.verbose_name_plural} were selected for deletion.",
            )
            return redirect(self.get_return_url(request))

        data.update({"table": table})
        return Response(data)


class ObjectBulkCreateViewMixin(NautobotViewSetMixin, BulkCreateModelMixin):
    """
    UI mixin to bulk create model instances.
    """

    bulk_create_active_tab = "csv-data"
    bulk_create_form_class = None
    bulk_create_widget_attrs = {}

    def _process_bulk_create_form(self, form):
        # Iterate through CSV data and bind each row to a new model form instance.
        new_objs = []
        request = self.request
        queryset = self.get_queryset()
        with transaction.atomic():
            if request.FILES:
                field_name = "csv_file"
                # Set the bulk_create_active_tab to "csv-file"
                # In case the form validation fails, the user will be redirected
                # to the tab with errors rendered on the form.
                self.bulk_create_active_tab = "csv-file"
            else:
                field_name = "csv_data"
            headers, records = form.cleaned_data[field_name]
            for row, data in enumerate(records, start=1):
                obj_form = self.bulk_create_form_class(data, headers=headers)
                restrict_form_fields(obj_form, request.user)

                if obj_form.is_valid():
                    obj = self.form_save(obj_form)
                    new_objs.append(obj)
                else:
                    for field, err in obj_form.errors.items():
                        form.add_error(field_name, f"Row {row} {field}: {err[0]}")
                    raise ValidationError("")

            # Enforce object-level permissions
            if queryset.filter(pk__in=[obj.pk for obj in new_objs]).count() != len(new_objs):
                raise ObjectDoesNotExist

        # Compile a table containing the imported objects
        table_class = self.get_table_class()
        obj_table = table_class(new_objs)
        if new_objs:
            msg = f"Imported {len(new_objs)} {new_objs[0]._meta.verbose_name_plural}"
            self.logger.info(msg)
            messages.success(request, msg)
        return obj_table

    def bulk_create(self, request, *args, **kwargs):
        context = {}
        if request.method == "POST":
            return self.perform_bulk_create(request)
        return Response(context)

    def perform_bulk_create(self, request):
        form_class = self.get_form_class()
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ObjectBulkUpdateViewMixin(NautobotViewSetMixin, BulkUpdateModelMixin):
    """
    UI mixin to bulk update model instances.
    """

    filterset_class = None
    bulk_update_form_class = None

    def _process_bulk_update_form(self, form):
        request = self.request
        queryset = self.get_queryset()
        model = queryset.model
        form_custom_fields = getattr(form, "custom_fields", [])
        form_relationships = getattr(form, "relationships", [])
        # Standard fields are those that are intrinsic to self.model in the form
        # Relationships, custom fields, object_note are extrinsic fields
        # PK is used to identify an existing instance, not to modify the object
        standard_fields = [
            field
            for field in form.fields
            if field not in form_custom_fields + form_relationships + ["pk"] + ["object_note"]
        ]
        nullified_fields = request.POST.getlist("_nullify")
        form_cf_to_key = {f"cf_{cf.slug}": cf.name for cf in CustomField.objects.get_for_model(model)}
        with transaction.atomic():
            updated_objects = []
            for obj in queryset.filter(pk__in=form.cleaned_data["pk"]):
                self.obj = obj
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
                    elif form.cleaned_data.get(field_name) not in (None, "", []):
                        obj.cf[form_cf_to_key[field_name]] = form.cleaned_data[field_name]

                obj.validated_save()
                updated_objects.append(obj)
                self.logger.debug(f"Saved {obj} (PK: {obj.pk})")

                # Add/remove tags
                if form.cleaned_data.get("add_tags", None):
                    obj.tags.add(*form.cleaned_data["add_tags"])
                if form.cleaned_data.get("remove_tags", None):
                    obj.tags.remove(*form.cleaned_data["remove_tags"])

                if hasattr(form, "save_relationships") and callable(form.save_relationships):
                    # Add/remove relationship associations
                    form.save_relationships(instance=obj, nullified_fields=nullified_fields)

                if hasattr(form, "save_note") and callable(form.save_note):
                    form.save_note(instance=obj, user=request.user)

            # Enforce object-level permissions
            if queryset.filter(pk__in=[obj.pk for obj in updated_objects]).count() != len(updated_objects):
                raise ObjectDoesNotExist
        if updated_objects:
            msg = f"Updated {len(updated_objects)} {model._meta.verbose_name_plural}"
            self.logger.info(msg)
            messages.success(self.request, msg)
        self.success_url = self.get_return_url(request)

    def bulk_update(self, request, *args, **kwargs):
        """
        Call perform_bulk_update().
        The function exist to keep the DRF's get/post pattern of {action}/perform_{action}, we will need it when we transition from using forms to serializers in the UI.
        User should override this function to handle any actions as needed before bulk update.
        """
        return self.perform_bulk_update(request, **kwargs)

    # TODO: this conflicts with BulkUpdateModelMixin.perform_bulk_update(self, objects, update_data, partial)
    def perform_bulk_update(self, request, **kwargs):  # pylint: disable=arguments-differ
        """
        request.POST "_edit": Function to render the user selection of objects in a table form/BulkUpdateForm via Response that is passed to NautobotHTMLRenderer.
        request.POST "_apply": Function to validate the table form/BulkUpdateForm and to perform the action of bulk update. Render the form with errors if exceptions are raised.
        """
        queryset = self.get_queryset()
        model = queryset.model

        # If we are editing *all* objects in the queryset, replace the PK list with all matched objects.
        if request.POST.get("_all"):
            if self.filterset_class is not None:
                self.pk_list = [obj.pk for obj in self.filterset_class(request.POST, model.objects.only("pk")).qs]
            else:
                self.pk_list = model.objects.values_list("pk", flat=True)
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
        table_class = self.get_table_class()
        table = table_class(queryset.filter(pk__in=self.pk_list), orderable=False)
        if not table.rows:
            messages.warning(
                request,
                f"No {queryset.model._meta.verbose_name_plural} were selected for deletion.",
            )
            return redirect(self.get_return_url(request))
        data.update({"table": table})
        return Response(data)
