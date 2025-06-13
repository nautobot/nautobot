from copy import deepcopy
import logging
import re
from typing import ClassVar, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError,
)
from django.db import IntegrityError, transaction
from django.db.models import Model, ProtectedError, Q, QuerySet
from django.forms import Form, ModelMultipleChoiceField, MultipleHiddenInput
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import resolve, reverse
from django.utils.encoding import iri_to_uri
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import View
from django_filters import FilterSet
from django_tables2 import RequestConfig, Table

from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.constants import MAX_PAGE_SIZE_DEFAULT
from nautobot.core.exceptions import AbortTransaction
from nautobot.core.forms import (
    BootstrapMixin,
    BulkRenameForm,
    ConfirmationForm,
    CSVDataField,
    CSVFileField,
    ImportForm,
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
    get_filterable_params_from_filter_params,
    normalize_querydict,
)
from nautobot.core.views.mixins import BulkEditAndBulkDeleteModelMixin, GetReturnURLMixin, ObjectPermissionRequiredMixin
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.utils import (
    check_filter_for_display,
    common_detail_view_context,
    get_csv_form_fields_from_serializer_class,
    get_saved_views_for_user,
    handle_protectederror,
    import_csv_helper,
    prepare_cloned_fields,
    view_changes_not_saved,
)
from nautobot.extras.models import ExportTemplate, SavedView, UserSavedViewAssociation


class GenericView(LoginRequiredMixin, View):
    """
    Base class for non-object-related views.

    Enforces authentication, which Django's base View does not by default.
    """


class ObjectView(ObjectPermissionRequiredMixin, View):
    """
    Retrieve a single object for display.

    queryset: The base queryset for retrieving the object
    template_name: Name of the template to use
    """

    queryset: ClassVar[Optional[QuerySet]] = None  # TODO: required, declared Optional only to avoid breaking change
    template_name: ClassVar[Optional[str]] = None
    object_detail_content = None

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
            request (Request): The current request
            instance (Model): The object being viewed

        Returns:
            (dict): Additional context data
        """
        return {
            "active_tab": request.GET.get("tab", "main"),
        }

    def get(self, request, *args, **kwargs):
        """
        Generic GET handler for accessing an object.
        """
        instance = get_object_or_404(self.queryset, **kwargs)
        content_type = ContentType.objects.get_for_model(self.queryset.model)
        context = {
            "object": instance,
            "content_type": content_type,
            "verbose_name": self.queryset.model._meta.verbose_name,
            "verbose_name_plural": self.queryset.model._meta.verbose_name_plural,
            "object_detail_content": self.object_detail_content,
            **common_detail_view_context(request, instance),
            **self.get_extra_context(request, instance),
        }

        return render(request, self.get_template_name(), context)


class ObjectListView(ObjectPermissionRequiredMixin, View):
    """
    List a series of objects.

    queryset: The queryset of objects to display. Note: Prefetching related objects is not necessary, as the
      table will prefetch objects as needed depending on the columns being displayed.
    filter: A django-filter FilterSet that is applied to the queryset
    filter_form: The form used to render filter options
    table: The django-tables2 Table used to render the objects list
    template_name: The name of the template
    non_filter_params: List of query parameters that are **not** used for queryset filtering
    """

    queryset: Optional[QuerySet] = None  # TODO: required, declared Optional only to avoid a breaking change
    filterset: Optional[type[FilterSet]] = None
    filterset_form: Optional[type[Form]] = None
    table: Optional[type[Table]] = None
    template_name = "generic/object_list.html"
    action_buttons = ("add", "import", "export")
    non_filter_params = (
        "export",  # trigger for CSV/export-template/YAML export # 3.0 TODO: remove, irrelevant after #4746
        "page",  # used by django-tables2.RequestConfig
        "per_page",  # used by get_paginate_count
        "sort",  # table sorting
        "saved_view",  # saved_view indicator pk or composite keys
        "table_changes_pending",  # indicator for if there is any table changes not applied to the saved view
        "all_filters_removed",  # indicator for if all filters have been removed from the saved view
        "clear_view",  # indicator for if the clear view button is clicked or not
    )

    def get_filter_params(self, request):
        """Helper function - take request.GET and discard any parameters that are not used for queryset filtering."""
        params = request.GET.copy()
        filter_params = get_filterable_params_from_filter_params(
            params,
            self.non_filter_params,
            self.filterset(),  # pylint: disable=not-callable  # this fn is only called if filterset is not None
        )
        if params.get("saved_view") and not filter_params and not params.get("all_filters_removed"):
            return SavedView.objects.get(pk=params.get("saved_view")).config.get("filter_params", {})
        return filter_params

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "view")

    # 3.0 TODO: remove, irrelevant after #4746
    def queryset_to_yaml(self):
        """
        Export the queryset of objects as concatenated YAML documents.
        """
        yaml_data = [obj.to_yaml() for obj in self.queryset]

        return "---\n".join(yaml_data)

    def validate_action_buttons(self, request):
        """Verify actions in self.action_buttons are valid view actions."""

        always_valid_actions = ("export",)
        valid_actions = []
        invalid_actions = []
        # added check for whether the action_buttons exist because of issue #2107
        if self.action_buttons is None:
            self.action_buttons = []
        for action in self.action_buttons:
            if action in always_valid_actions or validated_viewname(self.queryset.model, action) is not None:
                valid_actions.append(action)
            else:
                invalid_actions.append(action)
        if invalid_actions:
            messages.error(request, f"Missing views for action(s) {', '.join(invalid_actions)}")
        return valid_actions

    def get(self, request):
        model = self.queryset.model
        content_type = ContentType.objects.get_for_model(model)

        filter_params = request.GET
        user = request.user
        display_filter_params = []
        dynamic_filter_form = None
        filter_form = None
        hide_hierarchy_ui = False
        clear_view = request.GET.get("clear_view", False)
        resolved_path = resolve(request.path)
        list_url = f"{resolved_path.app_name}:{resolved_path.url_name}"

        skip_user_and_global_default_saved_view = False
        if self.filterset is not None:
            skip_user_and_global_default_saved_view = get_filterable_params_from_filter_params(
                request.GET.copy(),
                self.non_filter_params,
                self.filterset(),
            )

        # If the user clicks on the clear view button, we do not check for global or user defaults
        if not skip_user_and_global_default_saved_view and not clear_view and not request.GET.get("saved_view"):
            # Check if there is a default for this view for this specific user
            if not isinstance(user, AnonymousUser):
                try:
                    user_default_saved_view_pk = UserSavedViewAssociation.objects.get(
                        user=user, view_name=list_url
                    ).saved_view.pk
                    # Saved view should either belong to the user or be public
                    SavedView.objects.get(
                        Q(pk=user_default_saved_view_pk),
                        Q(owner=user) | Q(is_shared=True),
                    )
                    sv_url = reverse("extras:savedview", kwargs={"pk": user_default_saved_view_pk})
                    return redirect(sv_url)
                except ObjectDoesNotExist:
                    pass

            # Check if there is a global default for this view
            try:
                global_saved_view = SavedView.objects.get(view=list_url, is_global_default=True)
                return redirect(reverse("extras:savedview", kwargs={"pk": global_saved_view.pk}))
            except ObjectDoesNotExist:
                pass

        if self.filterset is not None:
            filter_params = self.get_filter_params(request)
            filterset = self.filterset(filter_params, self.queryset)  # pylint:disable=not-callable  # only if not None
            self.queryset = filterset.qs
            if not filterset.is_valid():
                messages.error(
                    request,
                    format_html("Invalid filters were specified: {}", filterset.errors),
                )
                self.queryset = self.queryset.none()

            # If a valid filterset is applied, we have to hide the hierarchy indentation in the UI for tables that support hierarchy indentation.
            # NOTE: An empty filterset query-param is also valid filterset and we dont want to hide hierarchy indentation if no filter query-param is provided
            #      hence `filterset.data`.
            if filterset.is_valid() and filterset.data:
                hide_hierarchy_ui = True

            display_filter_params = [
                check_filter_for_display(filterset.filters, field_name, values)
                for field_name, values in filter_params.items()
            ]

            if request.GET:
                factory_formset_params = convert_querydict_to_factory_formset_acceptable_querydict(
                    filter_params, filterset
                )
                dynamic_filter_form = DynamicFilterFormSet(filterset=filterset, data=factory_formset_params)
            else:
                dynamic_filter_form = DynamicFilterFormSet(filterset=filterset)

            if self.filterset_form is not None:
                filter_form = self.filterset_form(filter_params, label_suffix="")

        # Check for export template rendering
        if request.GET.get("export"):  # 3.0 TODO: remove, irrelevant after #4746
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
        elif "export" in request.GET and hasattr(model, "to_yaml"):  # 3.0 TODO: remove, irrelevant after #4746
            response = HttpResponse(self.queryset_to_yaml(), content_type="text/yaml")
            filename = f"{settings.BRANDING_PREPENDED_FILENAME}{self.queryset.model._meta.verbose_name_plural}.yaml"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        # Provide a hook to tweak the queryset based on the request immediately prior to rendering the object list
        self.queryset = self.alter_queryset(request)

        # Compile a dictionary indicating which permissions are available to the current user for this model
        permissions = {}
        for action in ("add", "change", "delete", "view"):
            perm_name = get_permission_for_model(model, action)
            permissions[action] = request.user.has_perm(perm_name)

        table = None
        table_config_form = None
        current_saved_view = None
        current_saved_view_pk = self.request.GET.get("saved_view", None)
        saved_views = get_saved_views_for_user(user, list_url)

        if current_saved_view_pk:
            try:
                # We are not using .restrict(request.user, "view") here
                # User should be able to see any saved view that he has the list view access to.
                current_saved_view = SavedView.objects.get(view=list_url, pk=current_saved_view_pk)
            except ObjectDoesNotExist:
                messages.error(request, f"Saved view {current_saved_view_pk} not found")

        # Construct the objects table
        if self.table is not None:
            if self.request.GET.getlist("sort") or (
                current_saved_view is not None and current_saved_view.config.get("sort_order")
            ):
                hide_hierarchy_ui = True  # hide tree hierarchy if custom sort is used
            table_changes_pending = self.request.GET.get("table_changes_pending", False)

            table = self.table(  # pylint: disable=not-callable  # we confirmed that self.table is not None
                self.queryset,
                table_changes_pending=table_changes_pending,
                saved_view=current_saved_view,
                user=request.user,
                hide_hierarchy_ui=hide_hierarchy_ui,
            )
            if "pk" in table.base_columns and (permissions["change"] or permissions["delete"]):
                table.columns.show("pk")

            # Apply the request context
            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request, current_saved_view),
            }
            RequestConfig(request, paginate).configure(table)
            table_config_form = TableConfigForm(table=table)
            max_page_size = get_settings_or_config("MAX_PAGE_SIZE", fallback=MAX_PAGE_SIZE_DEFAULT)
            if max_page_size and paginate["per_page"] > max_page_size:
                messages.warning(
                    request,
                    f'Requested "per_page" is too large. No more than {max_page_size} items may be displayed at a time.',
                )

        # For the search form field, use a custom placeholder.
        q_placeholder = "Search " + bettertitle(model._meta.verbose_name_plural)
        search_form = SearchForm(data=filter_params, q_placeholder=q_placeholder)

        valid_actions = self.validate_action_buttons(request)

        # Query SavedViews for dropdown button
        new_changes_not_applied = view_changes_not_saved(request, self, current_saved_view)

        context = {
            "content_type": content_type,
            "table": table,
            "permissions": permissions,
            "action_buttons": valid_actions,
            "table_config_form": table_config_form,
            "filter_params": display_filter_params,
            "filter_form": filter_form,
            "dynamic_filter_form": dynamic_filter_form,
            "search_form": search_form,
            "list_url": list_url,
            "title": bettertitle(model._meta.verbose_name_plural),
            "new_changes_not_applied": new_changes_not_applied,
            "current_saved_view": current_saved_view,
            "saved_views": saved_views,
            "model": model,
        }

        # `extra_context()` would require `request` access, however `request` parameter cannot simply be
        # added to `extra_context()` because  this method has been used by multiple apps without any parameters.
        # Changing 'def extra context()' to 'def extra context(request)' might break current methods
        # in plugins and core that either override or implement it without request.
        setattr(self, "request", request)
        context.update(self.extra_context())

        return render(request, self.template_name, context)

    def alter_queryset(self, request):
        # .all() is necessary to avoid caching queries
        return self.queryset.all()

    def extra_context(self):
        return {}


class ObjectEditView(GetReturnURLMixin, ObjectPermissionRequiredMixin, View):
    """
    Create or edit a single object.

    queryset: The base queryset for the object being modified
    model_form: The form used to create or edit the object
    template_name: The name of the template
    """

    queryset: Optional[QuerySet] = None  # TODO: required, declared Optional only to avoid a breaking change
    model_form: Optional[type[Form]] = None  # TODO: required, declared Optional only to avoid a breaking change
    template_name = "generic/object_create.html"

    def get_required_permission(self):
        # self._permission_action is set by dispatch() to either "add" or "change" depending on whether
        # we are modifying an existing object or creating a new one.
        return get_permission_for_model(self.queryset.model, self._permission_action)

    def get_object(self, kwargs):
        """Retrieve an object based on `kwargs`."""
        # Look up an existing object by PK, name, or slug, if provided.
        for field in ("pk", "name", "slug"):
            if field in kwargs:
                return get_object_or_404(self.queryset, **{field: kwargs[field]})
        return self.queryset.model()

    def get_extra_context(self, request, instance):
        """
        Return any additional context data for the template.

        Args:
            request (HttpRequest): The current request
            instance (Model): The object being edited

        Returns:
            (dict): Additional context data
        """
        return {}

    def alter_obj(self, obj, request, url_args, url_kwargs):
        # Allow views to add extra info to an object before it is processed. For example, a parent object can be defined
        # given some parameter from the request URL.
        return obj

    def dispatch(self, request, *args, **kwargs):
        # Determine required permission based on whether we are editing an existing object
        self._permission_action = "change" if kwargs else "add"

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        obj = self.alter_obj(self.get_object(kwargs), request, args, kwargs)

        initial_data = normalize_querydict(request.GET, form_class=self.model_form)
        if self.model_form is None:
            raise RuntimeError("self.model_form must not be None")
        form = self.model_form(instance=obj, initial=initial_data)  # pylint: disable=not-callable
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

    def successful_post(self, request, obj, created, logger):
        """Callback after the form is successfully saved but before redirecting the user."""
        verb = "Created" if created else "Modified"
        msg = f"{verb} {self.queryset.model._meta.verbose_name}"
        logger.info(f"{msg} {obj} (PK: {obj.pk})")
        try:
            msg = format_html('{} <a href="{}">{}</a>', msg, obj.get_absolute_url(), obj)
        except AttributeError:
            msg = format_html("{} {}", msg, obj)
        messages.success(request, msg)

    def post(self, request, *args, **kwargs):
        logger = logging.getLogger(__name__ + ".ObjectEditView")
        obj = self.alter_obj(self.get_object(kwargs), request, args, kwargs)
        if self.model_form is None:
            raise RuntimeError("self.model_form must not be None")
        form = self.model_form(  # pylint: disable=not-callable
            data=request.POST,
            files=request.FILES,
            initial=normalize_querydict(request.GET, form_class=self.model_form),
            instance=obj,
        )
        restrict_form_fields(form, request.user)

        if form.is_valid():
            logger.debug("Form validation was successful")

            try:
                with transaction.atomic():
                    object_created = not form.instance.present_in_database
                    obj = form.save()

                    # Check that the new object conforms with any assigned object-level permissions
                    self.queryset.get(pk=obj.pk)

                if hasattr(form, "save_note") and callable(form.save_note):
                    form.save_note(instance=obj, user=request.user)

                self.successful_post(request, obj, object_created, logger)

                if "_addanother" in request.POST:
                    # If the object has clone_fields, pre-populate a new instance of the form
                    if hasattr(obj, "clone_fields"):
                        url = f"{request.path}?{prepare_cloned_fields(obj)}"
                        return redirect(url)

                    return redirect(request.get_full_path())

                return_url = form.cleaned_data.get("return_url")
                if url_has_allowed_host_and_scheme(url=return_url, allowed_hosts=request.get_host()):
                    return redirect(iri_to_uri(return_url))
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


class ObjectDeleteView(GetReturnURLMixin, ObjectPermissionRequiredMixin, View):
    """
    Delete a single object.

    queryset: The base queryset for the object being deleted
    template_name: The name of the template
    """

    queryset: Optional[QuerySet] = None  # TODO: required, declared Optional only to avoid a breaking change
    template_name = "generic/object_delete.html"

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "delete")

    def get_object(self, kwargs):
        """Retrieve an object based on `kwargs`."""
        # Look up an existing object by PK, name, or slug, if provided.
        for field in ("pk", "name", "slug"):
            if field in kwargs:
                return get_object_or_404(self.queryset, **{field: kwargs[field]})
        return self.queryset.model()

    def get(self, request, **kwargs):
        obj = self.get_object(kwargs)
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

    def post(self, request, **kwargs):
        logger = logging.getLogger(__name__ + ".ObjectDeleteView")
        obj = self.get_object(kwargs)
        form = ConfirmationForm(request.POST)

        if form.is_valid():
            logger.debug("Form validation was successful")
            msg = f"Deleted {self.queryset.model._meta.verbose_name} {obj}"

            try:
                obj.delete()
            except ProtectedError as e:
                logger.info("Caught ProtectedError while attempting to delete object")
                handle_protectederror([obj], request, e)
                return redirect(obj.get_absolute_url())

            logger.info(msg)
            messages.success(request, msg)

            return_url = form.cleaned_data.get("return_url")
            if url_has_allowed_host_and_scheme(url=return_url, allowed_hosts=request.get_host()):
                return redirect(iri_to_uri(return_url))
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


class BulkCreateView(GetReturnURLMixin, ObjectPermissionRequiredMixin, View):
    """
    Create new objects in bulk.

    queryset: Base queryset for the objects being created
    form: Form class which provides the `pattern` field
    model_form: The ModelForm used to create individual objects
    pattern_target: Name of the field to be evaluated as a pattern (if any)
    template_name: The name of the template
    """

    queryset: Optional[QuerySet] = None  # TODO: required, declared Optional only to avoid a breaking change
    form: Optional[type[Form]] = None  # TODO: required, declared Optional only to avoid a breaking change
    model_form: Optional[type[Form]] = None  # TODO: required, declared Optional only to avoid a breaking change
    pattern_target = ""
    template_name = None

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "add")

    def get(self, request):
        # Set initial values for visible form fields from query args
        initial = {}
        if self.form is None or self.model_form is None:
            raise RuntimeError("self.form and self.model_form must not be None")
        for field in getattr(self.model_form._meta, "fields", []):
            if request.GET.get(field):
                initial[field] = request.GET[field]

        form = self.form()  # pylint: disable=not-callable
        model_form = self.model_form(initial=initial)  # pylint: disable=not-callable

        return render(
            request,
            self.template_name,
            {
                "obj_type": self.model_form._meta.model._meta.verbose_name,
                "form": form,
                "model_form": model_form,
                "return_url": self.get_return_url(request),
            },
        )

    def post(self, request):
        logger = logging.getLogger(__name__ + ".BulkCreateView")
        if self.queryset is None or self.form is None or self.model_form is None:
            raise RuntimeError("self.queryset, self.form, and self.model_form must not be None")
        model = self.queryset.model
        form = self.form(request.POST)  # pylint: disable=not-callable
        model_form = self.model_form(request.POST)  # pylint: disable=not-callable

        if form.is_valid():
            logger.debug("Form validation was successful")
            pattern = form.cleaned_data["pattern"]
            new_objs = []

            try:
                with transaction.atomic():
                    # Create objects from the expanded. Abort the transaction on the first validation error.
                    for value in pattern:
                        # Reinstantiate the model form each time to avoid overwriting the same instance. Use a mutable
                        # copy of the POST QueryDict so that we can update the target field value.
                        model_form = self.model_form(request.POST.copy())  # pylint: disable=not-callable
                        model_form.data[self.pattern_target] = value

                        # Validate each new object independently.
                        if model_form.is_valid():
                            obj = model_form.save()
                            logger.debug(f"Created {obj} (PK: {obj.pk})")
                            new_objs.append(obj)
                        else:
                            # Copy any errors on the pattern target field to the pattern form.
                            errors = model_form.errors.as_data()
                            if errors.get(self.pattern_target):
                                form.add_error("pattern", errors[self.pattern_target])
                            # Raise an IntegrityError to break the for loop and abort the transaction.
                            raise IntegrityError()

                    # Enforce object-level permissions
                    if self.queryset.filter(pk__in=[obj.pk for obj in new_objs]).count() != len(new_objs):
                        raise ObjectDoesNotExist

                    # If we make it to this point, validation has succeeded on all new objects.
                    msg = f"Added {len(new_objs)} {model._meta.verbose_name_plural}"
                    logger.info(msg)
                    messages.success(request, msg)

                    if "_addanother" in request.POST:
                        return redirect(request.path)
                    return redirect(self.get_return_url(request))

            except IntegrityError:
                pass

            except ObjectDoesNotExist:
                msg = "Object creation failed due to object-level permissions violation"
                logger.debug(msg)
                form.add_error(None, msg)

        else:
            logger.debug("Form validation failed")

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "model_form": model_form,
                "obj_type": model._meta.verbose_name,
                "return_url": self.get_return_url(request),
            },
        )


class ObjectImportView(GetReturnURLMixin, ObjectPermissionRequiredMixin, View):
    """
    Import a single object (YAML or JSON format).

    queryset: Base queryset for the objects being created
    model_form: The ModelForm used to create individual objects
    related_object_forms: A dictionary mapping of forms to be used for the creation of related (child) objects
    template_name: The name of the template
    """

    queryset: Optional[QuerySet] = None  # TODO: required, declared Optional only to avoid a breaking change
    model_form: Optional[type[Form]] = None  # TODO: required, declared Optional only to avoid a breaking change
    related_object_forms = {}
    template_name = "generic/object_import.html"

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "add")

    def get(self, request):
        form = ImportForm()

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "obj_type": self.queryset.model._meta.verbose_name,
                "return_url": self.get_return_url(request),
            },
        )

    def post(self, request):
        logger = logging.getLogger(__name__ + ".ObjectImportView")
        form = ImportForm(request.POST)

        if self.model_form is None or self.queryset is None:
            raise RuntimeError("self.model_form and self.queryset must not be None")

        if form.is_valid():
            logger.debug("Import form validation was successful")

            # Initialize model form
            data = form.cleaned_data["data"]
            model_form = self.model_form(data)  # pylint: disable=not-callable
            restrict_form_fields(model_form, request.user)

            # Assign default values for any fields which were not specified. We have to do this manually because passing
            # 'initial=' to the form on initialization merely sets default values for the widgets. Since widgets are not
            # used for YAML/JSON import, we first bind the imported data normally, then update the form's data with the
            # applicable field defaults as needed prior to form validation.
            for field_name, field in model_form.fields.items():
                if field_name not in data and hasattr(field, "initial"):
                    model_form.data[field_name] = field.initial

            if model_form.is_valid():
                try:
                    with transaction.atomic():
                        # Save the primary object
                        obj = model_form.save()

                        # Enforce object-level permissions
                        self.queryset.get(pk=obj.pk)

                        logger.debug(f"Created {obj} (PK: {obj.pk})")

                        # Iterate through the related object forms (if any), validating and saving each instance.
                        for (
                            field_name,
                            related_object_form,
                        ) in self.related_object_forms.items():
                            logger.debug(f"Processing form for related objects: {related_object_form}")

                            related_obj_pks = []
                            for i, rel_obj_data in enumerate(data.get(field_name, [])):
                                # add parent object key to related object data
                                rel_obj_data[obj._meta.verbose_name.replace(" ", "_")] = str(obj.pk)
                                f = related_object_form(rel_obj_data)

                                for subfield_name, field in f.fields.items():
                                    if subfield_name not in rel_obj_data and hasattr(field, "initial"):
                                        f.data[subfield_name] = field.initial

                                if f.is_valid():
                                    related_obj = f.save()
                                    related_obj_pks.append(related_obj.pk)
                                else:
                                    # Replicate errors on the related object form to the primary form for display
                                    for subfield_name, errors in f.errors.items():
                                        for err in errors:
                                            err_msg = f"{field_name}[{i}] {subfield_name}: {err}"
                                            model_form.add_error(None, err_msg)
                                    raise AbortTransaction()

                            # Enforce object-level permissions on related objects
                            model = related_object_form.Meta.model
                            if model.objects.filter(pk__in=related_obj_pks).count() != len(related_obj_pks):
                                raise ObjectDoesNotExist

                except AbortTransaction:
                    pass

                except ObjectDoesNotExist:
                    msg = "Object creation failed due to object-level permissions violation"
                    logger.debug(msg)
                    model_form.add_error(None, msg)

            if not model_form.errors:
                logger.info(f"Import object {obj} (PK: {obj.pk})")
                messages.success(
                    request,
                    format_html('Imported object: <a href="{}">{}</a>', obj.get_absolute_url(), obj),
                )

                if "_addanother" in request.POST:
                    return redirect(request.get_full_path())

                return_url = form.cleaned_data.get("return_url")
                if url_has_allowed_host_and_scheme(url=return_url, allowed_hosts=request.get_host()):
                    return redirect(iri_to_uri(return_url))
                else:
                    return redirect(self.get_return_url(request, obj))

            else:
                logger.debug("Model form validation failed")

                # Replicate model form errors for display
                for field, errors in model_form.errors.items():
                    for err in errors:
                        if field == "__all__":
                            form.add_error(None, err)
                        else:
                            form.add_error(None, f"{field}: {err}")

        else:
            logger.debug("Import form validation failed")

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "obj_type": self.queryset.model._meta.verbose_name,
                "return_url": self.get_return_url(request),
            },
        )


class BulkImportView(GetReturnURLMixin, ObjectPermissionRequiredMixin, View):  # 3.0 TODO: remove as it's no longer used
    """
    Import objects in bulk (CSV format).

    Deprecated - replaced by ImportObjects system Job.

    queryset: Base queryset for the model
    table: The django-tables2 Table used to render the list of imported objects
    template_name: The name of the template
    """

    queryset: Optional[QuerySet] = None  # TODO: required, declared Optional only to avoid a breaking change
    table: Optional[type[Table]] = None  # TODO: required, declared Optional only to avoid a breaking change
    template_name = "generic/object_bulk_import.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serializer_class = get_serializer_for_model(self.queryset.model)
        self.fields = get_csv_form_fields_from_serializer_class(self.serializer_class)
        self.required_field_names = [
            field["name"]
            for field in get_csv_form_fields_from_serializer_class(self.serializer_class)
            if field["required"]
        ]

    def _import_form(self, *args, **kwargs):
        class CSVImportForm(BootstrapMixin, Form):
            csv_data = CSVDataField(required_field_names=self.required_field_names)
            csv_file = CSVFileField()

        return CSVImportForm(*args, **kwargs)

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "add")

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "form": self._import_form(),
                "fields": self.fields,
                "obj_type": self.queryset.model._meta.verbose_name,
                "return_url": self.get_return_url(request),
                "active_tab": "csv-data",
            },
        )

    def post(self, request):
        logger = logging.getLogger(__name__ + ".BulkImportView")
        new_objs = []
        form = self._import_form(request.POST, request.FILES)

        if form.is_valid():
            logger.debug("Form validation was successful")

            if self.queryset is None or self.table is None:
                raise RuntimeError("self.queryset and self.table must not be None")

            try:
                # Iterate through CSV data and bind each row to a new model form instance.
                with transaction.atomic():
                    new_objs = import_csv_helper(request=request, form=form, serializer_class=self.serializer_class)

                    # Enforce object-level permissions
                    if self.queryset.filter(pk__in=[obj.pk for obj in new_objs]).count() != len(new_objs):
                        raise ObjectDoesNotExist

                # Compile a table containing the imported objects
                obj_table = self.table(new_objs)  # pylint: disable=not-callable

                if new_objs:
                    msg = f"Imported {len(new_objs)} {new_objs[0]._meta.verbose_name_plural}"
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
                "fields": self.fields,
                "obj_type": self.queryset.model._meta.verbose_name,
                "return_url": self.get_return_url(request),
                "active_tab": "csv-file" if form.has_error("csv_file") else "csv-data",
            },
        )


class BulkEditView(GetReturnURLMixin, ObjectPermissionRequiredMixin, BulkEditAndBulkDeleteModelMixin, View):
    """
    Edit objects in bulk.

    queryset: Custom queryset to use when retrieving objects (e.g. to select related objects)
    filter: FilterSet to apply when deleting by QuerySet
    table: The table used to display devices being edited
    form: The form class used to edit objects in bulk
    template_name: The name of the template
    """

    queryset: Optional[QuerySet] = None  # TODO: required, declared Optional only to avoid a breaking change
    filterset: Optional[type[FilterSet]] = None
    table: Optional[type[Table]] = None  # TODO: required, declared Optional only to avoid a breaking change
    form: Optional[type[Form]] = None  # TODO: required, declared Optional only to avoid a breaking change
    template_name = "generic/object_bulk_edit.html"

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "change")

    def get(self, request):
        return redirect(self.get_return_url(request))

    def alter_obj(self, obj, request, url_args, url_kwargs):
        # Allow views to add extra info to an object before it is processed.
        # For example, a parent object can be defined given some parameter from the request URL.
        return obj

    def extra_post_save_action(self, obj, form):
        """Extra actions after a form is saved"""

    def post(self, request, **kwargs):
        logger = logging.getLogger(__name__ + ".BulkEditView")
        if self.queryset is None or self.form is None or self.table is None:
            raise RuntimeError("self.queryset, self.form, and self.table must not be None")
        model = self.queryset.model
        edit_all = request.POST.get("_all")

        # If we are editing *all* objects in the queryset, replace the PK list with all matched objects.
        if edit_all:
            pk_list = []
            queryset = self._get_bulk_edit_delete_all_queryset(request)
        else:
            pk_list = request.POST.getlist("pk")
            queryset = self.queryset.filter(pk__in=pk_list)

        if "_apply" in request.POST:
            form = self.form(model, request.POST, edit_all=edit_all)  # pylint: disable=not-callable
            restrict_form_fields(form, request.user)

            if form.is_valid():
                logger.debug("Form validation was successful")
                return self.send_bulk_edit_objects_to_job(request, form.cleaned_data, model)
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

            form = self.form(model, initial=initial_data, edit_all=edit_all)  # pylint: disable=not-callable
            restrict_form_fields(form, request.user)

        # Retrieve objects being edited
        table = None
        if not edit_all:
            table = self.table(queryset, orderable=False)  # pylint: disable=not-callable
            if not table.rows:
                messages.warning(request, f"No {model._meta.verbose_name_plural} were selected.")
                return redirect(self.get_return_url(request))
            # Hide actions column if present
            if "actions" in table.columns:
                table.columns.hide("actions")

        context = {
            "form": form,
            "table": table,
            "obj_type_plural": model._meta.verbose_name_plural,
            "return_url": self.get_return_url(request),
            "objs_count": queryset.count(),
        }
        context.update(self.extra_context())
        return render(request, self.template_name, context)

    def extra_context(self):
        return {}


class BulkRenameView(GetReturnURLMixin, ObjectPermissionRequiredMixin, View):
    """
    An extendable view for renaming objects in bulk.
    """

    queryset: Optional[QuerySet] = None  # TODO: required, declared Optional only to avoid a breaking change
    template_name = "generic/object_bulk_rename.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create a new Form class from BulkRenameForm
        class _Form(BulkRenameForm):
            pk = ModelMultipleChoiceField(queryset=self.queryset, widget=MultipleHiddenInput())

        self.form = _Form

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "change")

    def post(self, request):
        logger = logging.getLogger(__name__ + ".BulkRenameView")
        query_pks = request.POST.getlist("pk")
        selected_objects = self.queryset.filter(pk__in=query_pks) if query_pks else None

        # selected_objects would return False; if no query_pks or invalid query_pks
        if not selected_objects:
            messages.warning(request, f"No valid {self.queryset.model._meta.verbose_name_plural} were selected.")
            return redirect(self.get_return_url(request))

        if "_preview" in request.POST or "_apply" in request.POST:
            form = self.form(request.POST, initial={"pk": query_pks})
            if form.is_valid():
                try:
                    with transaction.atomic():
                        renamed_pks = []
                        for obj in selected_objects:
                            find = form.cleaned_data["find"]
                            replace = form.cleaned_data["replace"]
                            if form.cleaned_data["use_regex"]:
                                try:
                                    obj.new_name = re.sub(find, replace, obj.name)
                                # Catch regex group reference errors
                                except re.error:
                                    obj.new_name = obj.name
                            else:
                                obj.new_name = obj.name.replace(find, replace)
                            renamed_pks.append(obj.pk)

                        if "_apply" in request.POST:
                            for obj in selected_objects:
                                obj.name = obj.new_name
                                obj.save()

                            # Enforce constrained permissions
                            if self.queryset.filter(pk__in=renamed_pks).count() != len(selected_objects):
                                raise ObjectDoesNotExist

                            messages.success(
                                request,
                                f"Renamed {len(selected_objects)} {self.queryset.model._meta.verbose_name_plural}",
                            )
                            return redirect(self.get_return_url(request))

                except ObjectDoesNotExist:
                    msg = "Object update failed due to object-level permissions violation"
                    logger.debug(msg)
                    form.add_error(None, msg)

        else:
            form = self.form(initial={"pk": query_pks})

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "obj_type_plural": self.queryset.model._meta.verbose_name_plural,
                "selected_objects": selected_objects,
                "return_url": self.get_return_url(request),
                "parent_name": self.get_selected_objects_parents_name(selected_objects),
            },
        )

    def get_selected_objects_parents_name(self, selected_objects):
        """
        Return selected_objects parent name.

        This method is intended to be overridden by child classes to return the parent name of the selected objects.

        Args:
            selected_objects (list[BaseModel]): The objects being renamed

        Returns:
            (str): The parent name of the selected objects
        """

        return ""


class BulkDeleteView(GetReturnURLMixin, ObjectPermissionRequiredMixin, BulkEditAndBulkDeleteModelMixin, View):
    """
    Delete objects in bulk.

    queryset: Custom queryset to use when retrieving objects (e.g. to select related objects)
    filterset: FilterSet to apply when deleting by QuerySet
    table: The table used to display devices being deleted
    form: The form class used to delete objects in bulk
    template_name: The name of the template
    """

    queryset: Optional[QuerySet] = None  # TODO: required, declared Optional only to avoid a breaking change
    filterset: Optional[type[FilterSet]] = None
    table: Optional[type[Table]] = None  # TODO: required, declared Optional only to avoid a breaking change
    form: Optional[type[Form]] = None
    template_name = "generic/object_bulk_delete.html"

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "delete")

    def get(self, request):
        return redirect(self.get_return_url(request))

    def post(self, request, **kwargs):
        logger = logging.getLogger(f"{__name__}.BulkDeleteView")
        if self.queryset is None or self.table is None:
            raise RuntimeError("self.queryset and self.table must not be None")
        model = self.queryset.model
        delete_all = request.POST.get("_all")

        # Are we deleting *all* objects in the queryset or just a selected subset?
        if delete_all:
            queryset = self._get_bulk_edit_delete_all_queryset(request)
            pk_list = []
        else:
            pk_list = request.POST.getlist("pk")
            queryset = self.queryset.filter(pk__in=pk_list)

        form_cls = self.get_form()

        if "_confirm" in request.POST:
            form = form_cls(request.POST)
            # Set pk field requirement here instead of BulkDeleteForm since get_form() may return a different form class
            if delete_all:
                form.fields["pk"].required = False

            if form.is_valid():
                logger.debug("Form validation was successful")
                return self.send_bulk_delete_objects_to_job(request, pk_list, model, delete_all)
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
        table = None
        if not delete_all:
            table = self.table(queryset, orderable=False)  # pylint: disable=not-callable
            if not table.rows:
                messages.warning(
                    request,
                    f"No {model._meta.verbose_name_plural} were selected for deletion.",
                )
                return redirect(self.get_return_url(request))
            # Hide actions column if present
            if "actions" in table.columns:
                table.columns.hide("actions")

        context = {
            "form": form,
            "obj_type_plural": model._meta.verbose_name_plural,
            "table": table,
            "return_url": self.get_return_url(request),
            "total_objs_to_delete": queryset.count(),
            "delete_all": delete_all,
        }
        context.update(self.extra_context())
        return render(request, self.template_name, context)

    def perform_pre_delete(self, request, queryset):
        pass

    def extra_context(self):
        return {}

    def get_form(self):
        """
        Provide a standard bulk delete form if none has been specified for the view
        """

        class BulkDeleteForm(ConfirmationForm):
            pk = ModelMultipleChoiceField(queryset=self.queryset, widget=MultipleHiddenInput)

        if self.form:
            return self.form

        return BulkDeleteForm


#
# Device/VirtualMachine components
#


# TODO: Replace with BulkCreateView
class ComponentCreateView(GetReturnURLMixin, ObjectPermissionRequiredMixin, View):
    """
    Add one or more components (e.g. interfaces, console ports, etc.) to a Device or VirtualMachine.
    """

    queryset: Optional[QuerySet] = None  # TODO: required, declared Optional only to avoid a breaking change
    form: Optional[type[Form]] = None  # TODO: required, declared Optional only to avoid a breaking change
    model_form: Optional[type[Form]] = None  # TODO: required, declared Optional only to avoid a breaking change
    template_name = "dcim/device_component_add.html"

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "add")

    def get(self, request):
        if self.form is None or self.model_form is None:
            raise RuntimeError("self.form and self.model_form must not be None")
        form = self.form(initial=normalize_querydict(request.GET, form_class=self.form))  # pylint: disable=not-callable
        model_form = self.model_form(request.GET)  # pylint: disable=not-callable

        return render(
            request,
            self.template_name,
            {
                "component_type": self.queryset.model._meta.verbose_name,
                "model_form": model_form,
                "form": form,
                "return_url": self.get_return_url(request),
            },
        )

    def post(self, request):
        logger = logging.getLogger(__name__ + ".ComponentCreateView")
        if self.form is None or self.model_form is None or self.queryset is None:
            raise RuntimeError("self.form, self.model_form, and self.queryset must not be None")
        form = self.form(request.POST, initial=normalize_querydict(request.GET, form_class=self.form))  # pylint: disable=not-callable
        model_form = self.model_form(request.POST, initial=normalize_querydict(request.GET, form_class=self.model_form))  # pylint: disable=not-callable

        if form.is_valid():
            new_components = []
            data = deepcopy(request.POST)

            names = form.cleaned_data["name_pattern"]
            labels = form.cleaned_data.get("label_pattern")
            for i, name in enumerate(names):
                label = labels[i] if labels else None
                # Initialize the individual component form
                data["name"] = name
                data["label"] = label
                if hasattr(form, "get_iterative_data"):
                    data.update(form.get_iterative_data(i))
                component_form = self.model_form(  # pylint: disable=not-callable
                    data, initial=normalize_querydict(request.GET, form_class=self.model_form)
                )

                if component_form.is_valid():
                    new_components.append(component_form)
                else:
                    for field, errors in component_form.errors.as_data().items():
                        # Assign errors on the child form's name/label field to name_pattern/label_pattern on the parent form
                        if field == "name":
                            field = "name_pattern"
                        elif field == "label":
                            field = "label_pattern"
                        for e in errors:
                            err_str = ", ".join(e)
                            form.add_error(field, f"{name}: {err_str}")

            if not form.errors:
                try:
                    with transaction.atomic():
                        # Create the new components
                        new_objs = []
                        for component_form in new_components:
                            obj = component_form.save()
                            new_objs.append(obj)

                        # Enforce object-level permissions
                        if self.queryset.filter(pk__in=[obj.pk for obj in new_objs]).count() != len(new_objs):
                            raise ObjectDoesNotExist

                    messages.success(
                        request,
                        f"Added {len(new_components)} {self.queryset.model._meta.verbose_name_plural}",
                    )
                    if "_addanother" in request.POST:
                        return redirect(request.get_full_path())
                    else:
                        return redirect(self.get_return_url(request))

                except ObjectDoesNotExist:
                    msg = "Component creation failed due to object-level permissions violation"
                    logger.debug(msg)
                    form.add_error(None, msg)

        return render(
            request,
            self.template_name,
            {
                "component_type": self.queryset.model._meta.verbose_name,
                "form": form,
                "model_form": model_form,
                "return_url": self.get_return_url(request),
            },
        )


class BulkComponentCreateView(GetReturnURLMixin, ObjectPermissionRequiredMixin, View):
    """
    Add one or more components (e.g. interfaces, console ports, etc.) to a set of Devices or VirtualMachines.
    """

    parent_model: Optional[type[Model]] = None  # TODO: required, declared Optional only to avoid a breaking change
    parent_field = None
    form: Optional[type[Form]] = None  # TODO: required, declared Optional only to avoid a breaking change
    queryset: Optional[QuerySet] = None  # TODO: required, declared Optional only to avoid a breaking change
    model_form: Optional[type[Form]] = None  # TODO: required, declared Optional only to avoid a breaking change
    filterset: Optional[type[FilterSet]] = None
    table: Optional[type[Table]] = None  # TODO: required, declared Optional only to avoid a breaking change
    template_name = "generic/object_bulk_add_component.html"

    def get_required_permission(self):
        return f"dcim.add_{self.queryset.model._meta.model_name}"

    def post(self, request):
        logger = logging.getLogger(__name__ + ".BulkComponentCreateView")
        if (
            self.form is None
            or self.model_form is None
            or self.parent_model is None
            or self.queryset is None
            or self.table is None
        ):
            raise RuntimeError(
                "self.form, self.model_form, self.parent_model, self.queryset, and self.table must not be None"
            )
        parent_model_name = self.parent_model._meta.verbose_name_plural
        model_name = self.queryset.model._meta.verbose_name_plural
        model = self.queryset.model

        # Are we editing *all* objects in the queryset or just a selected subset?
        if request.POST.get("_all") and self.filterset is not None:
            pk_list = [obj.pk for obj in self.filterset(request.GET, self.parent_model.objects.only("pk")).qs]  # pylint: disable=not-callable
        else:
            pk_list = request.POST.getlist("pk")

        selected_objects = self.parent_model.objects.filter(pk__in=pk_list)
        if not selected_objects:
            messages.warning(
                request,
                f"No {self.parent_model._meta.verbose_name_plural} were selected.",
            )
            return redirect(self.get_return_url(request))
        table = self.table(selected_objects)  # pylint: disable=not-callable

        if "_create" in request.POST:
            form = self.form(model, request.POST)  # pylint: disable=not-callable

            if form.is_valid():
                logger.debug("Form validation was successful")

                new_components = []
                data = deepcopy(form.cleaned_data)

                try:
                    with transaction.atomic():
                        for obj in data["pk"]:
                            names = data["name_pattern"]
                            labels = data["label_pattern"] if "label_pattern" in data else None
                            for i, name in enumerate(names):
                                label = labels[i] if labels else None

                                component_data = {
                                    self.parent_field: obj.pk,
                                    "name": name,
                                    "label": label,
                                }
                                component_data.update(data)
                                component_form = self.model_form(component_data)  # pylint: disable=not-callable
                                if component_form.is_valid():
                                    instance = component_form.save()
                                    logger.debug(f"Created {instance} on {instance.parent}")
                                    new_components.append(instance)
                                else:
                                    for (
                                        field,
                                        errors,
                                    ) in component_form.errors.as_data().items():
                                        for e in errors:
                                            err_str = ", ".join(e)
                                            form.add_error(
                                                field,
                                                f"{obj} {name}: {err_str}",
                                            )

                        # Enforce object-level permissions
                        if self.queryset.filter(pk__in=[obj.pk for obj in new_components]).count() != len(
                            new_components
                        ):
                            raise ObjectDoesNotExist

                except IntegrityError:
                    pass

                except ObjectDoesNotExist:
                    msg = "Component creation failed due to object-level permissions violation"
                    logger.debug(msg)
                    form.add_error(None, msg)

                if not form.errors:
                    msg = f"Added {len(new_components)} {model_name} to {len(form.cleaned_data['pk'])} {parent_model_name}."
                    logger.info(msg)
                    messages.success(request, msg)

                    return redirect(self.get_return_url(request))

            else:
                logger.debug("Form validation failed")

        else:
            form = self.form(model, initial={"pk": pk_list})  # pylint: disable=not-callable

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "parent_model_name": parent_model_name,
                "model_name": model_name,
                "table": table,
                "return_url": self.get_return_url(request),
            },
        )
