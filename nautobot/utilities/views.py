import logging

from django.conf import settings
from django.contrib.auth.mixins import AccessMixin
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.http import is_safe_url
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import (
    FieldDoesNotExist,
    ImproperlyConfigured,
    ObjectDoesNotExist,
    ValidationError,
)
from django.db import transaction
from django.db.models import ManyToManyField, ProtectedError
from django.forms import Form, ModelMultipleChoiceField, MultipleHiddenInput, Textarea
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views.generic import View
from django_tables2 import RequestConfig
from rest_framework.routers import Route

from nautobot.utilities.permissions import get_permission_for_model, resolve_permission
from nautobot.extras.models import CustomField, ExportTemplate
from nautobot.utilities.error_handlers import handle_protectederror
from nautobot.utilities.forms import (
    BootstrapMixin,
    ConfirmationForm,
    CSVDataField,
    CSVFileField,
    TableConfigForm,
    restrict_form_fields,
)
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.utils import (
    csv_format,
    normalize_querydict,
    prepare_cloned_fields,
)

#
# View Mixins
#


class ContentTypePermissionRequiredMixin(AccessMixin):
    """
    Similar to Django's built-in PermissionRequiredMixin, but extended to check model-level permission assignments.
    This is related to ObjectPermissionRequiredMixin, except that is does not enforce object-level permissions,
    and fits within Nautobot's custom permission enforcement system.

    additional_permissions: An optional iterable of statically declared permissions to evaluate in addition to those
                            derived from the object type
    """

    additional_permissions = list()

    def get_required_permission(self):
        """
        Return the specific permission necessary to perform the requested action on an object.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement get_required_permission()")

    def has_permission(self):
        user = self.request.user
        permission_required = self.get_required_permission()

        # Check that the user has been granted the required permission(s).
        if user.has_perms((permission_required, *self.additional_permissions)):
            return True

        return False

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class ObjectPermissionRequiredMixin(AccessMixin):
    """
    Similar to Django's built-in PermissionRequiredMixin, but extended to check for both model-level and object-level
    permission assignments. If the user has only object-level permissions assigned, the view's queryset is filtered
    to return only those objects on which the user is permitted to perform the specified action.

    additional_permissions: An optional iterable of statically declared permissions to evaluate in addition to those
                            derived from the object type
    """

    additional_permissions = list()

    def get_required_permission(self):
        """
        Return the specific permission necessary to perform the requested action on an object.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement get_required_permission()")

    def has_permission(self):
        user = self.request.user
        permission_required = self.get_required_permission()

        # Check that the user has been granted the required permission(s).
        if user.has_perms((permission_required, *self.additional_permissions)):

            # Update the view's QuerySet to filter only the permitted objects
            action = resolve_permission(permission_required)[1]
            self.queryset = self.queryset.restrict(user, action)

            return True

        return False

    def dispatch(self, request, *args, **kwargs):

        if not hasattr(self, "queryset"):
            raise ImproperlyConfigured(
                "{} has no queryset defined. ObjectPermissionRequiredMixin may only be used on views which define "
                "a base queryset".format(self.__class__.__name__)
            )

        if not self.has_permission():
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class GetReturnURLMixin:
    """
    Provides logic for determining where a user should be redirected after processing a form.
    """

    default_return_url = None

    def get_return_url(self, request, obj=None):

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
        if hasattr(self, "queryset"):
            model_opts = self.queryset.model._meta
            try:
                prefix = "plugins:" if model_opts.app_label in settings.PLUGINS else ""
                return reverse(f"{prefix}{model_opts.app_label}:{model_opts.model_name}_list")
            except NoReverseMatch:
                pass

        # If all else fails, return home. Ideally this should never happen.
        return reverse("home")


class NautobotRouterMixin:

    routes = None
    model = None
    queryset = None
    table = None
    prefetch_related = []
    template_name = None

    @property
    def detail_queryset(self):
        return self.model.objects.all()

    @property
    def table_queryset(self):
        return self.model.objects.prefetch_related(*self.prefetch_related)

    def define_routes(self):
        self.routes = []


class ObjectDetailViewMixin(NautobotRouterMixin):
    """
    Retrieve a single object for display.
    queryset: The base queryset for retrieving the object
    template_name: Name of the template to use
    """

    def define_routes(self):
        super().define_routes()
        self.routes.append(
            Route(
                url=r"^{prefix}/{lookup}/$",
                mapping={
                    "get": "handle_object_detail_get",
                },
                name="{basename}",
                detail=True,
                initkwargs={"suffix": "Detail"},
            ),
        )

    def get_extra_context_for_detail(self, request, instance):
        """
        Return any additional context data for the template.
        request: The current request
        instance: The object being viewed
        """
        return {}

    def handle_object_detail_get(self, request, *args, **kwargs):
        """
        Generic GET handler for accessing an object by PK or slug
        """
        instance = get_object_or_404(self.queryset, **kwargs)

        return render(
            request,
            self.template_name,
            {
                "object": instance,
                "verbose_name": self.queryset.model._meta.verbose_name,
                "verbose_name_plural": self.queryset.model._meta.verbose_name_plural,
                **self.get_extra_context_for_detail(request, instance),
            },
        )


class ObjectListViewMixin(NautobotRouterMixin):
    """
    List a series of objects.
    queryset: The queryset of objects to display. Note: Prefetching related objects is not necessary, as the
      table will prefetch objects as needed depending on the columns being displayed.
    filter: A django-filter FilterSet that is applied to the queryset
    filter_form: The form used to render filter options
    table: The django-tables2 Table used to render the objects list
    template_name: The name of the template
    """

    object_list_filterset = None
    object_list_filterset_form = None
    object_list_action_buttons = ("add", "import", "export")

    def define_routes(self):
        super().define_routes()
        self.routes.append(
            Route(
                url=r"^{prefix}/$",
                mapping={
                    "get": "handle_object_list_get",
                },
                name="{basename}_list",
                detail=False,
                initkwargs={"suffix": "List"},
            ),
        )

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

    def handle_object_list_get(self, request):
        model = self.queryset.model
        content_type = ContentType.objects.get_for_model(model)

        if self.object_list_filterset:
            self.queryset = self.object_list_filterset(request.GET, self.queryset).qs

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
            filename = "nautobot_{}.yaml".format(self.queryset.model._meta.verbose_name_plural)
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
            return response

        # Fall back to built-in CSV formatting if export requested but no template specified
        elif "export" in request.GET and hasattr(model, "to_csv"):
            response = HttpResponse(self.queryset_to_csv(), content_type="text/csv")
            filename = "nautobot_{}.csv".format(self.queryset.model._meta.verbose_name_plural)
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
            return response

        # Provide a hook to tweak the queryset based on the request immediately prior to rendering the object list
        self.queryset = self.alter_queryset_for_list(request)

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

        context = {
            "content_type": content_type,
            "table": table,
            "permissions": permissions,
            "action_buttons": self.object_list_action_buttons,
            "table_config_form": TableConfigForm(table=table),
            "filter_form": self.object_list_filterset_form(request.GET, label_suffix="")
            if self.object_list_filterset_form
            else None,
        }
        context.update(self.extra_context_for_list())

        return render(request, self.template_name, context)

    def alter_queryset_for_list(self, request):
        # .all() is necessary to avoid caching queries
        return self.queryset.all()

    def extra_context_for_list(self):
        return {}


class ObjectEditViewMixin(GetReturnURLMixin, NautobotRouterMixin):
    """
    Create or edit a single object.
    queryset: The base queryset for the object being modified
    model_form: The form used to create or edit the object
    template_name: The name of the template
    """

    object_edit_model_form = None

    def define_routes(self):
        super().define_routes()
        self.routes.append(
            Route(
                url=r"^{prefix}/add/$",
                mapping={
                    "get": "handle_object_edit_get",
                    "post": "handle_object_edit_post",
                },
                name="{basename}_add",
                detail=False,
                initkwargs={"suffix": "Add"},
            ),
        )
        self.routes.append(
            Route(
                url=r"^{prefix}/{lookup}/edit/$",
                mapping={
                    "get": "handle_object_edit_get",
                    "post": "handle_object_edit_post",
                },
                name="{basename}_edit",
                detail=True,
                initkwargs={"suffix": "Edit"},
            ),
        )

    def get_object_for_edit(self, kwargs):
        # Look up an existing object by slug or PK, if provided.
        if "slug" in kwargs:
            return get_object_or_404(self.queryset, slug=kwargs["slug"])
        elif "pk" in kwargs:
            return get_object_or_404(self.queryset, pk=kwargs["pk"])
        # Otherwise, return a new instance.
        return self.queryset.model()

    def alter_obj_for_edit(self, obj, request, url_args, url_kwargs):
        # Allow views to add extra info to an object before it is processed. For example, a parent object can be defined
        # given some parameter from the request URL.
        return obj

    def handle_object_edit_get(self, request, *args, **kwargs):
        obj = self.alter_obj_for_edit(self.get_object_for_edit(kwargs), request, args, kwargs)

        initial_data = normalize_querydict(request.GET)
        form = self.object_edit_model_form(instance=obj, initial=initial_data)
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
            },
        )

    def handle_object_edit_post(self, request, *args, **kwargs):
        logger = logging.getLogger("nautobot.views.ObjectEditView")
        obj = self.alter_obj_for_edit(self.get_object_for_edit(kwargs), request, args, kwargs)
        form = self.object_edit_model_form(data=request.POST, files=request.FILES, instance=obj)
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
            self.object_edit_template_name,
            {
                "obj": obj,
                "obj_type": self.queryset.model._meta.verbose_name,
                "form": form,
                "return_url": self.get_return_url(request, obj),
                "editing": obj.present_in_database,
            },
        )


class ObjectDeleteViewMixin(GetReturnURLMixin, NautobotRouterMixin):
    """
    Delete a single object.
    queryset: The base queryset for the object being deleted
    template_name: The name of the template
    """

    def define_routes(self):
        super().define_routes()
        self.routes.append(
            Route(
                url=r"^{prefix}/{lookup}/delete/$",
                mapping={
                    "get": "handle_object_delete_get",
                    "post": "handle_object_delete_post",
                },
                name="{basename}_delete",
                detail=True,
                initkwargs={"suffix": "Delete"},
            ),
        )

    def get_object_for_delete(self, kwargs):
        # Look up object by slug if one has been provided. Otherwise, use PK.
        if "slug" in kwargs:
            return get_object_or_404(self.queryset, slug=kwargs["slug"])
        else:
            return get_object_or_404(self.queryset, pk=kwargs["pk"])

    def handle_object_delete_get(self, request, **kwargs):
        obj = self.get_object_for_delete(kwargs)
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

    def handle_object_delete_post(self, request, **kwargs):
        logger = logging.getLogger("nautobot.views.ObjectDeleteView")
        obj = self.get_object_for_delete(kwargs)
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
            self.object_delete_template_name,
            {
                "obj": obj,
                "form": form,
                "obj_type": self.queryset.model._meta.verbose_name,
                "return_url": self.get_return_url(request, obj),
            },
        )


class BulkImportViewMixin(GetReturnURLMixin, NautobotRouterMixin):
    """
    Import objects in bulk (CSV format).
    queryset: Base queryset for the model
    model_form: The form used to create each imported object
    table: The django-tables2 Table used to render the list of imported objects
    template_name: The name of the template
    widget_attrs: A dict of attributes to apply to the import widget (e.g. to require a session key)
    """

    bulk_import_model_form = None
    bulk_import_widget_attrs = {}

    def define_routes(self):
        super().define_routes()
        self.routes.append(
            Route(
                url=r"^{prefix}/import/$",
                mapping={
                    "get": "handle_bulk_import_get",
                    "post": "handle_bulk_import_post",
                },
                name="{basename}_import",
                detail=False,
                initkwargs={"suffix": "Import"},
            ),
        )

    def _import_form_for_bulk_import(self, *args, **kwargs):
        class ImportForm(BootstrapMixin, Form):
            csv_data = CSVDataField(
                from_form=self.bulk_import_model_form, widget=Textarea(attrs=self.bulk_import_widget_attrs)
            )
            csv_file = CSVFileField(from_form=self.bulk_import_model_form)

        return ImportForm(*args, **kwargs)

    def _save_obj_for_bulk_import(self, obj_form, request):
        """
        Provide a hook to modify the object immediately before saving it (e.g. to encrypt secret data).
        """
        return obj_form.save()

    def handle_bulk_import_get(self, request):
        return render(
            request,
            self.template_name,
            {
                "form": self._import_form_for_bulk_import(),
                "fields": self.bulk_import_model_form().fields,
                "obj_type": self.bulk_import_model_form._meta.model._meta.verbose_name,
                "return_url": self.get_return_url(request),
                "active_tab": "csv-data",
            },
        )

    def handle_bulk_import_post(self, request):
        logger = logging.getLogger("nautobot.views.BulkImportView")
        new_objs = []
        form = self._import_form_for_bulk_import(request.POST)

        if form.is_valid():
            logger.debug("Form validation was successful")

            try:
                # Iterate through CSV data and bind each row to a new model form instance.
                with transaction.atomic():
                    headers, records = form.cleaned_data["csv_data"]
                    for row, data in enumerate(records, start=1):
                        obj_form = self.bulk_import_model_form(data, headers=headers)
                        restrict_form_fields(obj_form, request.user)

                        if obj_form.is_valid():
                            obj = self._save_obj_for_bulk_import(obj_form, request)
                            new_objs.append(obj)
                        else:
                            for field, err in obj_form.errors.items():
                                form.add_error("csv", "Row {} {}: {}".format(row, field, err[0]))
                            raise ValidationError("")

                    # Enforce object-level permissions
                    if self.queryset.filter(pk__in=[obj.pk for obj in new_objs]).count() != len(new_objs):
                        raise ObjectDoesNotExist

                # Compile a table containing the imported objects
                obj_table = self.table(new_objs)

                if new_objs:
                    msg = "Imported {} {}".format(len(new_objs), new_objs[0]._meta.verbose_name_plural)
                    logger.info(msg)
                    messages.success(request, msg)

                    return render(
                        request,
                        "import_success.html",
                        {
                            "table": obj_table,
                            "return_url": self.get_return_url(request),
                        },
                    )

            except ValidationError:
                pass

            except ObjectDoesNotExist:
                msg = "Object import failed due to object-level permissions violation"
                logger.debug(msg)
                form.add_error(None, msg)

        else:
            logger.debug("Form validation failed")

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "fields": self.bulk_import_model_form().fields,
                "obj_type": self.bulk_import_model_form._meta.model._meta.verbose_name,
                "return_url": self.get_return_url(request),
            },
        )


class BulkEditViewMixin(GetReturnURLMixin, NautobotRouterMixin):
    """
    Edit objects in bulk.
    queryset: Custom queryset to use when retrieving objects (e.g. to select related objects)
    filter: FilterSet to apply when deleting by QuerySet
    table: The table used to display devices being edited
    form: The form class used to edit objects in bulk
    template_name: The name of the template
    """

    bulk_edit_filterset = None
    bulk_edit_form = None

    def define_routes(self):
        super().define_routes()
        self.routes.append(
            Route(
                url=r"^{prefix}/edit/$",
                mapping={
                    "get": "handle_bulk_edit_get",
                    "post": "handle_bulk_edit_post",
                },
                name="{basename}_bulk_edit",
                detail=False,
                initkwargs={"suffix": "Bulk Edit"},
            ),
        )

    def handle_bulk_edit_get(self, request):
        return redirect(self.get_return_url(request))

    def alter_obj_for_bulk_edit(self, obj, request, url_args, url_kwargs):
        # Allow views to add extra info to an object before it is processed.
        # For example, a parent object can be defined given some parameter from the request URL.
        return obj

    def handle_bulk_edit_post(self, request, **kwargs):
        logger = logging.getLogger("nautobot.views.BulkEditView")
        model = self.queryset.model

        # If we are editing *all* objects in the queryset, replace the PK list with all matched objects.
        if request.POST.get("_all") and self.bulk_edit_filterset is not None:
            pk_list = [obj.pk for obj in self.bulk_edit_filterset(request.GET, self.queryset.only("pk")).qs]
        else:
            pk_list = request.POST.getlist("pk")

        if "_apply" in request.POST:
            form = self.bulk_edit_form(model, request.POST)
            restrict_form_fields(form, request.user)

            if form.is_valid():
                logger.debug("Form validation was successful")
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
                            logger.debug(f"Saved {obj} (PK: {obj.pk})")

                            # Add/remove tags
                            if form.cleaned_data.get("add_tags", None):
                                obj.tags.add(*form.cleaned_data["add_tags"])
                            if form.cleaned_data.get("remove_tags", None):
                                obj.tags.remove(*form.cleaned_data["remove_tags"])

                        # Enforce object-level permissions
                        if self.queryset.filter(pk__in=[obj.pk for obj in updated_objects]).count() != len(
                            updated_objects
                        ):
                            raise ObjectDoesNotExist

                    if updated_objects:
                        msg = "Updated {} {}".format(len(updated_objects), model._meta.verbose_name_plural)
                        logger.info(msg)
                        messages.success(self.request, msg)

                    return redirect(self.get_return_url(request))

                except ValidationError as e:
                    messages.error(self.request, "{} failed validation: {}".format(obj, e))

                except ObjectDoesNotExist:
                    msg = "Object update failed due to object-level permissions violation"
                    logger.debug(msg)
                    form.add_error(None, msg)

            else:
                logger.debug("Form validation failed")

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

            form = self.bulk_edit_form(model, initial=initial_data)
            restrict_form_fields(form, request.user)

        # Retrieve objects being edited
        table = self.table(self.queryset.filter(pk__in=pk_list), orderable=False)
        if not table.rows:
            messages.warning(request, "No {} were selected.".format(model._meta.verbose_name_plural))
            return redirect(self.get_return_url(request))

        context = {
            "form": form,
            "table": table,
            "obj_type_plural": model._meta.verbose_name_plural,
            "return_url": self.get_return_url(request),
        }
        context.update(self.extra_context_for_bulk_edit())
        return render(request, self.template_name, context)

    def extra_context_for_bulk_edit(self):
        return {}


class BulkDeleteViewMixin(GetReturnURLMixin, NautobotRouterMixin):
    """
    Delete objects in bulk.
    queryset: Custom queryset to use when retrieving objects (e.g. to select related objects)
    filter: FilterSet to apply when deleting by QuerySet
    table: The table used to display devices being deleted
    form: The form class used to delete objects in bulk
    template_name: The name of the template
    """

    bulk_delete_filterset = None
    bulk_delete_form = None

    def define_routes(self):
        super().define_routes()
        self.routes.append(
            Route(
                url=r"^{prefix}/delete/$",
                mapping={
                    "get": "handle_bulk_delete_get",
                    "post": "handle_bulk_delete_post",
                },
                name="{basename}_bulk_delete",
                detail=False,
                initkwargs={"suffix": "Bulk Delete"},
            ),
        )

    def handle_bulk_delete_get(self, request):
        return redirect(self.get_return_url(request))

    def handle_bulk_delete_post(self, request, **kwargs):
        logger = logging.getLogger("nautobot.views.BulkDeleteView")
        model = self.queryset.model

        # Are we deleting *all* objects in the queryset or just a selected subset?
        if request.POST.get("_all"):
            if self.bulk_delete_filterset is not None:
                pk_list = [obj.pk for obj in self.bulk_delete_filterset(request.GET, model.objects.only("pk")).qs]
            else:
                pk_list = model.objects.values_list("pk", flat=True)
        else:
            pk_list = request.POST.getlist("pk")

        form_cls = self.get_form_for_bulk_delete()

        if "_confirm" in request.POST:
            form = form_cls(request.POST)
            if form.is_valid():
                logger.debug("Form validation was successful")

                # Delete objects
                queryset = self.queryset.filter(pk__in=pk_list)
                try:
                    deleted_count = queryset.delete()[1][model._meta.label]
                except ProtectedError as e:
                    logger.info("Caught ProtectedError while attempting to delete objects")
                    handle_protectederror(queryset, request, e)
                    return redirect(self.get_return_url(request))

                msg = "Deleted {} {}".format(deleted_count, model._meta.verbose_name_plural)
                logger.info(msg)
                messages.success(request, msg)
                return redirect(self.get_return_url(request))

            else:
                logger.debug("Form validation failed")

        else:
            form = form_cls(
                initial={
                    "pk": pk_list,
                    "return_url": self.get_return_url(request),
                }
            )

        # Retrieve objects being deleted
        table = self.table(self.queryset.filter(pk__in=pk_list), orderable=False)
        if not table.rows:
            messages.warning(
                request,
                "No {} were selected for deletion.".format(model._meta.verbose_name_plural),
            )
            return redirect(self.get_return_url(request))

        context = {
            "form": form,
            "obj_type_plural": model._meta.verbose_name_plural,
            "table": table,
            "return_url": self.get_return_url(request),
        }
        context.update(self.extra_context_for_bulk_delete())
        return render(request, self.template_name, context)

    def extra_context_for_bulk_delete(self):
        return {}

    def get_form_for_bulk_delete(self):
        """
        Provide a standard bulk delete form if none has been specified for the view
        """

        class BulkDeleteForm(ConfirmationForm):
            pk = ModelMultipleChoiceField(queryset=self.queryset, widget=MultipleHiddenInput)

        if self.bulk_delete_form:
            return self.bulk_delete_form

        return BulkDeleteForm


#
# Views
#


class ObjectView(ObjectPermissionRequiredMixin, ObjectDetailViewMixin, View):
    queryset = None
    template_name = None

    def __init__(self, *args, **kwargs):
        if self.template_name:
            self.object_detail_template_name = self.template_name
        super().__init__(*args, **kwargs)

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "view")

    def get(self, request, *args, **kwargs):
        return self.handle_object_detail_get(request, *args, **kwargs)


class ObjectListView(ObjectPermissionRequiredMixin, ObjectListViewMixin, View):
    filterset = None
    filterset_form = None
    table = None
    template_name = None
    action_buttons = None

    def __init__(self, *args, **kwargs):
        if self.filterset:
            self.object_list_filterset = self.filterset
        if self.filterset_form:
            self.object_list_filterset_form = self.filterset_form
        # if self.table:
        #     self.object_list_table = self.table
        if self.template_name:
            self.object_list_template_name = self.template_name
        if self.action_buttons:
            self.object_list_action_buttons = self.action_buttons
        super().__init__(*args, **kwargs)

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "view")

    def get(self, request):
        return self.handle_object_list_get(request)


class ObjectEditView(ObjectPermissionRequiredMixin, ObjectEditViewMixin, View):
    queryset = None
    model_form = None
    template_name = None

    def __init__(self, *args, **kwargs):
        if self.model_form:
            self.object_edit_model_form = self.model_form
        if self.template_name:
            self.object_edit_template_name = self.template_name
        super().__init__(*args, **kwargs)

    def get_required_permission(self):
        # self._permission_action is set by dispatch() to either "add" or "change" depending on whether
        # we are modifying an existing object or creating a new one.
        return get_permission_for_model(self.queryset.model, self._permission_action)

    def dispatch(self, request, *args, **kwargs):
        # Determine required permission based on whether we are editing an existing object
        self._permission_action = "change" if kwargs else "add"

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.handle_object_edit_get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.handle_object_edit_post(request, *args, **kwargs)


class ObjectDeleteView(ObjectPermissionRequiredMixin, ObjectDeleteViewMixin, View):
    queryset = None
    template_name = None

    def __init__(self, *args, **kwargs):
        if self.queryset:
            self.queryset = self.queryset
        if self.template_name:
            self.object_delete_template_name = self.template_name
        super().__init__(*args, **kwargs)

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "delete")

    def get(self, request, **kwargs):
        return self.handle_object_delete_get(request, **kwargs)

    def post(self, request, **kwargs):
        return self.handle_object_delete_post(request, **kwargs)


class BulkImportView(ObjectPermissionRequiredMixin, BulkImportViewMixin, View):
    queryset = None
    model_form = None
    table = None
    template_name = None
    widget_attrs = None

    def __init__(self, *args, **kwargs):
        if self.queryset:
            self.queryset = self.queryset
        if self.model_form:
            self.bulk_import_model_form = self.model_form
        # if self.table:
        #     self.bulk_import_table = self.table
        if self.template_name:
            self.bulk_import_template_name = self.template_name
        if self.widget_attrs:
            self.bulk_import_widget_attrs = self.widget_attrs
        super().__init__(*args, **kwargs)

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "add")

    def get(self, request):
        return self.handle_bulk_import_get(request)

    def post(self, request):
        return self.handle_bulk_import_post(request)


class BulkEditView(ObjectPermissionRequiredMixin, BulkEditViewMixin, View):
    queryset = None
    filterset = None
    table = None
    form = None
    template_name = None

    def __init__(self, *args, **kwargs):
        if self.queryset:
            self.queryset = self.queryset
        if self.filterset:
            self.bulk_edit_filterset = self.filterset
        # if self.table:
        #     self.bulk_edit_table = self.table
        if self.form:
            self.bulk_edit_form = self.form
        if self.template_name:
            self.bulk_edit_template_name = self.template_name
        super().__init__(*args, **kwargs)

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "change")

    def get(self, request):
        return self.handle_bulk_edit_get(request)

    def post(self, request, **kwargs):
        return self.handle_bulk_edit_post(request, **kwargs)


class BulkDeleteView(ObjectPermissionRequiredMixin, BulkDeleteViewMixin, View):
    queryset = None
    filterset = None
    table = None
    form = None
    template_name = None

    def __init__(self, *args, **kwargs):
        if self.queryset:
            self.queryset = self.queryset
        if self.filterset:
            self.bulk_delete_filterset = self.filterset
        # if self.table:
        #     self.bulk_delete_table = self.table
        if self.form:
            self.bulk_delete_form = self.form
        # if self.template_name:
        #     self.bulk_delete_template_name = self.template_name
        super().__init__(*args, **kwargs)

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "delete")

    def get(self, request):
        return self.handle_bulk_delete_get(request)

    def post(self, request, **kwargs):
        return self.handle_bulk_delete_post(request, **kwargs)
