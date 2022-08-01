import logging
from functools import update_wrapper

from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
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
from django.utils.decorators import classonlymethod
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import FormView

from rest_framework import generics, mixins
from rest_framework_bulk import mixins as bulk_mixins
from rest_framework.response import Response
from rest_framework.viewsets import ViewSetMixin

from nautobot.extras.models import CustomField, ExportTemplate, ChangeLoggedModel
from nautobot.utilities.permissions import get_permission_for_model
from nautobot.utilities.error_handlers import handle_protectederror
from nautobot.utilities.forms import (
    BootstrapMixin,
    ConfirmationForm,
    CSVDataField,
    CSVFileField,
    restrict_form_fields,
)
from nautobot.utilities.renderers import NautobotHTMLRenderer
from nautobot.utilities.utils import (
    csv_format,
    prepare_cloned_fields,
)
from nautobot.utilities.views import ObjectPermissionRequiredMixin, GetReturnURLMixin

PERMISSIONS_ACTION_MAP = {
    "list": "view",
    "retrieve": "view",
    "destroy": "delete",
    "create_or_update": "change",
    "bulk_create": "add",
    "bulk_destroy": "delete",
    "bulk_edit": "change",
}


class NautobotViewSetMixin(
    ViewSetMixin, ObjectPermissionRequiredMixin, GetReturnURLMixin, FormView, generics.GenericAPIView
):
    serializer_class = None
    renderer_classes = [NautobotHTMLRenderer]

    def alter_queryset(self, request):
        # .all() is necessary to avoid caching queries
        return self.queryset.all()

    def alter_obj_for_edit(self, obj, request, url_args, url_kwargs):
        # Allow views to add extra info to an object before it is processed. For example, a parent object can be defined
        # given some parameter from the request URL.
        return obj

    def form_valid(self, obj, form, **kwargs):
        self.logger.debug("Form validation was successful")
        request = self.request
        if self.action == "destroy":
            try:
                obj.delete()
            except ProtectedError as e:
                self.logger.info("Caught ProtectedError while attempting to delete object")
                handle_protectederror([obj], request, e)
                return redirect(obj.get_absolute_url())

            msg = f"Deleted {self.queryset.model._meta.verbose_name} {obj}"
            self.logger.info(msg)
            messages.success(request, msg)
            self.success_url = self.get_return_url(request)
            return super().form_valid(form)

        elif self.action == "bulk_destroy":
            pk_list = kwargs.pop("pk_list")
            model = self.queryset.model
            # Delete objects
            queryset = self.queryset.filter(pk__in=pk_list)
            try:
                deleted_count = queryset.delete()[1][model._meta.label]
            except ProtectedError as e:
                self.logger.info("Caught ProtectedError while attempting to delete objects")
                handle_protectederror(queryset, request, e)
                self.success_url = self.get_return_url(request)
                return super().form_valid(form)
            msg = f"Deleted {deleted_count} {model._meta.verbose_name_plural}"
            self.logger.info(msg)
            self.success_url = self.get_return_url(request)
            messages.success(request, msg)
            return super().form_valid(form)

        elif self.action == "create_or_update":
            try:
                with transaction.atomic():
                    object_created = not form.instance.present_in_database
                    obj = form.save()

                    # Check that the new object conforms with any assigned object-level permissions
                    self.queryset.get(pk=obj.pk)
                msg = f'{"Created" if object_created else "Modified"} {self.queryset.model._meta.verbose_name}'
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
                        return redirect(url)
                    return redirect(request.get_full_path())
                return_url = form.cleaned_data.get("return_url")
                if return_url is not None and is_safe_url(url=return_url, allowed_hosts=request.get_host()):
                    self.success_url = return_url
                else:
                    self.success_url = self.get_return_url(request, obj)
                return super().form_valid(form)
            except ObjectDoesNotExist:
                msg = "Object save failed due to object-level permissions violation"
                self.logger.debug(msg)
                form.add_error(None, msg)

        elif self.action == "bulk_edit":
            model = self.queryset.model
            custom_fields = form.custom_fields if hasattr(form, "custom_fields") else []
            standard_fields = [field for field in form.fields if field not in custom_fields + ["pk"]]
            nullified_fields = request.POST.getlist("_nullify")
            try:
                with transaction.atomic():
                    updated_objects = []
                    for obj in self.queryset.filter(pk__in=form.cleaned_data["pk"]):
                        obj = self.alter_obj_for_bulk_edit(obj, request, [], kwargs)
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
                                    setattr(obj, name, None if model_field.null else "")
                            # ManyToManyFields
                            elif isinstance(model_field, ManyToManyField):
                                if form.cleaned_data[name]:
                                    getattr(obj, name).set(form.cleaned_data[name])
                            # Normal fields
                            elif form.cleaned_data[name] not in (None, ""):
                                setattr(obj, name, form.cleaned_data[name])
                        # Update custom fields
                        for name in custom_fields:
                            if name in form.nullable_fields and name in nullified_fields:
                                obj.cf[name] = None
                            elif form.cleaned_data.get(name) not in (None, ""):
                                obj.cf[name] = form.cleaned_data[name]

                        obj.full_clean()
                        obj.save()
                        updated_objects.append(obj)
                        self.logger.debug(f"Saved {obj} (PK: {obj.pk})")

                        # Add/remove tags
                        if form.cleaned_data.get("add_tags", None):
                            obj.tags.add(*form.cleaned_data["add_tags"])
                        if form.cleaned_data.get("remove_tags", None):
                            obj.tags.remove(*form.cleaned_data["remove_tags"])

                    # Enforce object-level permissions
                    if self.queryset.filter(pk__in=[obj.pk for obj in updated_objects]).count() != len(updated_objects):
                        raise ObjectDoesNotExist
                if updated_objects:
                    msg = f"Updated {len(updated_objects)} {model._meta.verbose_name_plural}"
                    self.logger.info(msg)
                    messages.success(self.request, msg)
                self.success_url = self.get_return_url(request)
                return super().form_valid(form)
            except ValidationError as e:
                messages.error(self.request, f"{obj} failed validation: {e}")
            except ObjectDoesNotExist:
                msg = "Object update failed due to object-level permissions violation"
                self.logger.debug(msg)
                form.add_error(None, msg)

        elif self.action == "bulk_create":
            new_objs = []
            try:
                # Iterate through CSV data and bind each row to a new model form instance.
                with transaction.atomic():
                    headers, records = form.cleaned_data["csv_data"]
                    for row, data in enumerate(records, start=1):
                        obj_form = self.import_form(data, headers=headers)
                        restrict_form_fields(obj_form, request.user)

                        if obj_form.is_valid():
                            obj = self._save_obj_for_bulk_import(obj_form, request)
                            new_objs.append(obj)
                        else:
                            for field, err in obj_form.errors.items():
                                form.add_error("csv_data", f"Row {row} {field}: {err[0]}")
                            raise ValidationError("")

                    # Enforce object-level permissions
                    if self.queryset.filter(pk__in=[obj.pk for obj in new_objs]).count() != len(new_objs):
                        raise ObjectDoesNotExist

                # Compile a table containing the imported objects
                obj_table = self.table(new_objs)
                if new_objs:
                    msg = f"Imported {len(new_objs)} {new_objs[0]._meta.verbose_name_plural}"
                    self.logger.info(msg)
                    messages.success(request, msg)
                    return Response(
                        {
                            "table": obj_table,
                            "return_url": self.get_return_url(request),
                            "template": "import_success.html",
                        },
                    )
            except ValidationError:
                pass

            except ObjectDoesNotExist:
                msg = "Object import failed due to object-level permissions violation"
                self.logger.debug(msg)
                form.add_error(None, msg)

        data = {}
        if self.action == "bulk_edit" or self.action == "bulk_delete":
            pk_list = kwargs.pop("pk_list")
            table = self.table(self.queryset.filter(pk__in=pk_list), orderable=False)
            if not table.rows:
                messages.warning(
                    request,
                    f"No {self.queryset.model._meta.verbose_name_plural} were selected for deletion.",
                )
                return redirect(self.get_return_url(request))

            data = {
                "table": table,
            }
        data.update({"form": form})
        return Response(data)

    def form_invalid(self, form):
        context = {}
        context.update({"form": form})
        self.logger.debug("Form Validation Failed")
        if self.action == "bulk_edit" or self.action == "bulk_destroy":
            return context
        return Response(context)

    def get_object(self):
        """
        Returns the object the view is displaying.
        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if lookup_url_kwarg not in self.kwargs:
            return self.queryset.model()
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_extra_context(self, request, view_type, instance=None):
        """
        Return any additional context data for the template.
        request: The current request
        instance: The object being viewed
        """
        return {}

    def get_template_name(self, view_type):
        # Use "<app>/<model>_<view_type> if available, else fall back to generic templates
        model_opts = self.model._meta
        app_label = model_opts.app_label
        if view_type == "detail":
            return f"{app_label}/{model_opts.model_name}.html"

        try:
            select_template([f"{app_label}/{model_opts.model_name}_{view_type}.html"])
            return f"{app_label}/{model_opts.model_name}_{view_type}.html"
        except TemplateDoesNotExist:
            return f"generic/object_{view_type}.html"

    def initial(self, request, *args, **kwargs):
        """
        Runs anything that needs to occur prior to calling the method handler.
        """
        self.format_kwarg = self.get_format_suffix(**kwargs)

        # Perform content negotiation and store the accepted info on the request
        neg = self.perform_content_negotiation(request)
        request.accepted_renderer, request.accepted_media_type = neg

        # Determine the API version, if versioning is in use.
        version, scheme = self.determine_version(request, *args, **kwargs)
        request.version, request.versioning_scheme = version, scheme

        # Ensure that the incoming request is permitted
        self.perform_authentication(request)
        self.check_permissions(request)
        self.check_throttles(request)

    @classonlymethod
    def as_view(cls, actions=None, **initkwargs):
        """
        Because of the way class based views create a closure around the
        instantiated view, we need to totally reimplement `.as_view`,
        and slightly modify the view function that is created and returned.
        """
        # The name and description initkwargs may be explicitly overridden for
        # certain route confiugurations. eg, names of extra actions.
        cls.name = None
        cls.description = None

        # The suffix initkwarg is reserved for displaying the viewset type.
        # This initkwarg should have no effect if the name is provided.
        # eg. 'List' or 'Instance'.
        cls.suffix = None

        # The detail initkwarg is reserved for introspecting the viewset type.
        cls.detail = None

        # Setting a basename allows a view to reverse its action urls. This
        # value is provided by the router through the initkwargs.
        cls.basename = None

        # actions must not be empty
        if not actions:
            raise TypeError(
                "The `actions` argument must be provided when "
                "calling `.as_view()` on a ViewSet. For example "
                "`.as_view({'get': 'list'})`"
            )

        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError(
                    "You tried to pass in the %s method name as a "
                    "keyword argument to %s(). Don't do that." % (key, cls.__name__)
                )
            if not hasattr(cls, key):
                raise TypeError("%s() received an invalid keyword %r" % (cls.__name__, key))

        # name and suffix are mutually exclusive
        if "name" in initkwargs and "suffix" in initkwargs:
            raise TypeError(
                "%s() received both `name` and `suffix`, which are mutually exclusive arguments." % (cls.__name__)
            )

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            # We also store the mapping of request methods to actions,
            # so that we can later set the action attribute.
            # eg. `self.action = 'list'` on an incoming GET request.
            self.action_map = actions

            # Bind methods to actions
            # This is the bit that's different to a standard view
            for method, action in actions.items():
                handler = getattr(self, action)
                setattr(self, method, handler)

            if hasattr(self, "get") and not hasattr(self, "head"):
                self.head = self.get

            self.request = request
            self.args = args
            self.kwargs = kwargs
            self.action = action

            # And continue as usual
            return self.dispatch(request, *args, **kwargs)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())

        # We need to set these on the view function, so that breadcrumb
        # generation can pick out these bits of information from a
        # resolved URL.
        view.cls = cls
        view.initkwargs = initkwargs
        view.actions = actions
        return csrf_exempt(view)


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
    filterset_form = None

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
        context = {}
        if "export" in request.GET:
            model = self.queryset.model
            content_type = ContentType.objects.get_for_model(model)
            return self.check_for_export(request, model, content_type)
        return Response(context)


class ObjectDeleteViewMixin(NautobotViewSetMixin, mixins.DestroyModelMixin):
    logger = logging.getLogger("nautobot.views.ObjectDeleteView")

    def destroy(self, request, *args, **kwargs):
        context = {}
        if request.method == "POST":
            return self.perform_destroy(request, **kwargs)
        return Response(context)

    def perform_destroy(self, request, **kwargs):
        obj = self.get_object()
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            return self.form_valid(obj, form)
        else:
            return self.form_invalid(form)


class ObjectEditViewMixin(NautobotViewSetMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin):
    logger = logging.getLogger("nautobot.views.ObjectEditView")

    def create_or_update(self, request, *args, **kwargs):
        context = {}
        if request.method == "POST":
            return self.perform_create_or_update(request, *args, **kwargs)
        return Response(context)

    def perform_create_or_update(self, request, *args, **kwargs):
        obj = self.alter_obj_for_edit(self.get_object(), request, args, kwargs)
        form = self.form(data=request.POST, files=request.FILES, instance=obj)
        restrict_form_fields(form, request.user)
        if form.is_valid():
            return self.form_valid(obj, form)
        else:
            return self.form_invalid(form)


class BulkDeleteViewMixin(NautobotViewSetMixin, bulk_mixins.BulkDestroyModelMixin):
    bulk_delete_form = None
    logger = logging.getLogger("nautobot.views.BulkDeleteView")

    def get_form(self):
        """
        Provide a standard bulk delete form if none has been specified for the view
        """

        class BulkDeleteForm(ConfirmationForm):
            pk = ModelMultipleChoiceField(queryset=self.queryset, widget=MultipleHiddenInput)

        if self.bulk_delete_form:
            return self.bulk_delete_form

        return BulkDeleteForm

    def bulk_destroy(self, request, *args, **kwargs):
        if request.method == "POST":
            return self.perform_bulk_destroy(request, **kwargs)

    def perform_bulk_destroy(self, request, **kwargs):
        model = self.queryset.model
        # Are we deleting *all* objects in the queryset or just a selected subset?
        if request.POST.get("_all"):
            if self.bulk_delete_filterset is not None:
                pk_list = [obj.pk for obj in self.bulk_delete_filterset(request.GET, model.objects.only("pk")).qs]
            else:
                pk_list = model.objects.values_list("pk", flat=True)
        else:
            pk_list = request.POST.getlist("pk")

        form_cls = self.get_form()
        data = {}
        if "_confirm" in request.POST:
            form = form_cls(request.POST)
            if form.is_valid():
                return self.form_valid(obj=None, form=form, pk_list=pk_list)
            else:
                data = self.form_invalid(form)
        table = self.table(self.queryset.filter(pk__in=pk_list), orderable=False)
        if not table.rows:
            messages.warning(
                request,
                f"No {self.queryset.model._meta.verbose_name_plural} were selected for deletion.",
            )
            return redirect(self.get_return_url(request))

        data.update({"table": table})
        return Response(data)


class BulkImportViewMixin(NautobotViewSetMixin, bulk_mixins.BulkCreateModelMixin):
    bulk_import_widget_attrs = {}
    logger = logging.getLogger("nautobot.views.BulkImportView")

    def _import_form_for_bulk_import(self, *args, **kwargs):
        class ImportForm(BootstrapMixin, Form):
            csv_data = CSVDataField(from_form=self.import_form, widget=Textarea(attrs=self.bulk_import_widget_attrs))
            csv_file = CSVFileField(from_form=self.import_form)

        return ImportForm(*args, **kwargs)

    def _save_obj_for_bulk_import(self, obj_form, request):
        """
        Provide a hook to modify the object immediately before saving it (e.g. to encrypt secret data).
        """
        return obj_form.save()

    def bulk_create(self, request):
        context = {}
        if request.method == "POST":
            return self.perform_bulk_create(request)
        return Response(context)

    def perform_bulk_create(self, request):
        form = self._import_form_for_bulk_import(request.POST)
        if form.is_valid():
            return self.form_valid(obj=None, form=form)
        else:
            return self.form_invalid(form)


class BulkUpdateViewMixin(NautobotViewSetMixin, bulk_mixins.BulkUpdateModelMixin):
    bulk_edit_filterset = None
    bulk_edit_form = None
    logger = logging.getLogger("nautobot.views.BulkEditView")

    def alter_obj_for_bulk_edit(self, obj, request, url_args, url_kwargs):
        # Allow views to add extra info to an object before it is processed.
        # For example, a parent object can be defined given some parameter from the request URL.
        return obj

    def bulk_edit(self, request, *args, **kwargs):
        if request.method == "POST":
            return self.perform_bulk_edit(request, **kwargs)

    def perform_bulk_edit(self, request, **kwargs):
        model = self.queryset.model

        # If we are editing *all* objects in the queryset, replace the PK list with all matched objects.
        if request.POST.get("_all") and self.bulk_edit_filterset is not None:
            pk_list = [obj.pk for obj in self.bulk_edit_filterset(request.GET, self.queryset.only("pk")).qs]
        else:
            pk_list = request.POST.getlist("pk")
        data = {}
        if "_apply" in request.POST:
            form = self.bulk_edit_form(model, request.POST)
            restrict_form_fields(form, request.user)
            if form.is_valid():
                return self.form_valid(obj=None, form=form, pk_list=pk_list, **kwargs)
            else:
                data = self.form_invalid(form)

        table = self.table(self.queryset.filter(pk__in=pk_list), orderable=False)
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
    ObjectDeleteViewMixin,
    BulkDeleteViewMixin,
    BulkImportViewMixin,
    BulkUpdateViewMixin,
):
    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, PERMISSIONS_ACTION_MAP[self.action])
