from datetime import timedelta
import logging

from celery import chain
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.forms.utils import pretty_name
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template, TemplateDoesNotExist
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import iri_to_uri
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import View
from django_tables2 import RequestConfig
from jsonschema.validators import Draft7Validator

from nautobot.core.forms import restrict_form_fields
from nautobot.core.models.querysets import count_related
from nautobot.core.models.utils import pretty_print_query
from nautobot.core.tables import ButtonsColumn
from nautobot.core.utils.lookup import get_table_for_model
from nautobot.core.utils.requests import normalize_querydict
from nautobot.core.views import generic, viewsets
from nautobot.core.views.mixins import (
    ObjectBulkDestroyViewMixin,
    ObjectBulkUpdateViewMixin,
    ObjectDestroyViewMixin,
    ObjectEditViewMixin,
    ObjectPermissionRequiredMixin,
)
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.utils import prepare_cloned_fields
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.dcim.models import Controller, Device, Interface, Location, Rack
from nautobot.dcim.tables import ControllerTable, DeviceTable, RackTable
from nautobot.extras.constants import JOB_OVERRIDABLE_FIELDS
from nautobot.extras.tasks import delete_custom_field_data
from nautobot.extras.utils import get_base_template, get_worker_count
from nautobot.ipam.models import IPAddress, Prefix, VLAN
from nautobot.ipam.tables import IPAddressTable, PrefixTable, VLANTable
from nautobot.virtualization.models import VirtualMachine, VMInterface
from nautobot.virtualization.tables import VirtualMachineTable

from . import filters, forms, tables
from .api import serializers
from .choices import JobExecutionType, JobResultStatusChoices, LogLevelChoices
from .datasources import (
    enqueue_git_repository_diff_origin_and_local,
    enqueue_pull_git_repository_and_refresh_data,
    get_datasource_contents,
)
from .filters import RoleFilterSet
from .forms import RoleBulkEditForm, RoleForm
from .jobs import get_job
from .models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    Contact,
    ContactAssociation,
    CustomField,
    CustomLink,
    DynamicGroup,
    ExportTemplate,
    ExternalIntegration,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job as JobModel,
    JobButton,
    JobHook,
    JobLogEntry,
    JobResult,
    Note,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    Role,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    Tag,
    TaggedItem,
    Team,
    Webhook,
)
from .registry import registry
from .tables import AssociatedContactsTable, RoleTable

logger = logging.getLogger(__name__)


#
# Computed Fields
#


class ComputedFieldListView(generic.ObjectListView):
    queryset = ComputedField.objects.all()
    table = tables.ComputedFieldTable
    filterset = filters.ComputedFieldFilterSet
    filterset_form = forms.ComputedFieldFilterForm
    action_buttons = ("add",)


class ComputedFieldView(generic.ObjectView):
    queryset = ComputedField.objects.all()


class ComputedFieldEditView(generic.ObjectEditView):
    queryset = ComputedField.objects.all()
    model_form = forms.ComputedFieldForm
    template_name = "extras/computedfield_edit.html"


class ComputedFieldDeleteView(generic.ObjectDeleteView):
    queryset = ComputedField.objects.all()


class ComputedFieldBulkDeleteView(generic.BulkDeleteView):
    queryset = ComputedField.objects.all()
    table = tables.ComputedFieldTable
    filterset = filters.ComputedFieldFilterSet


#
# Config contexts
#

# TODO(Glenn): disallow (or at least warn) user from manually editing config contexts that
# have an associated owner, such as a Git repository


class ConfigContextListView(generic.ObjectListView):
    queryset = ConfigContext.objects.all()
    filterset = filters.ConfigContextFilterSet
    filterset_form = forms.ConfigContextFilterForm
    table = tables.ConfigContextTable
    action_buttons = ("add",)


class ConfigContextView(generic.ObjectView):
    queryset = ConfigContext.objects.all()

    def get_extra_context(self, request, instance):
        # Determine user's preferred output format
        if request.GET.get("format") in ["json", "yaml"]:
            format_ = request.GET.get("format")
            if request.user.is_authenticated:
                request.user.set_config("extras.configcontext.format", format_, commit=True)
        elif request.user.is_authenticated:
            format_ = request.user.get_config("extras.configcontext.format", "json")
        else:
            format_ = "json"

        return {
            "format": format_,
        }


class ConfigContextEditView(generic.ObjectEditView):
    queryset = ConfigContext.objects.all()
    model_form = forms.ConfigContextForm
    template_name = "extras/configcontext_edit.html"


class ConfigContextBulkEditView(generic.BulkEditView):
    queryset = ConfigContext.objects.all()
    filterset = filters.ConfigContextFilterSet
    table = tables.ConfigContextTable
    form = forms.ConfigContextBulkEditForm


class ConfigContextDeleteView(generic.ObjectDeleteView):
    queryset = ConfigContext.objects.all()


class ConfigContextBulkDeleteView(generic.BulkDeleteView):
    queryset = ConfigContext.objects.all()
    table = tables.ConfigContextTable
    filterset = filters.ConfigContextFilterSet


class ObjectConfigContextView(generic.ObjectView):
    base_template = None
    template_name = "extras/object_configcontext.html"

    def get_extra_context(self, request, instance):
        source_contexts = ConfigContext.objects.restrict(request.user, "view").get_for_object(instance)

        # Determine user's preferred output format
        if request.GET.get("format") in ["json", "yaml"]:
            format_ = request.GET.get("format")
            if request.user.is_authenticated:
                request.user.set_config("extras.configcontext.format", format_, commit=True)
        elif request.user.is_authenticated:
            format_ = request.user.get_config("extras.configcontext.format", "json")
        else:
            format_ = "json"

        return {
            "rendered_context": instance.get_config_context(),
            "source_contexts": source_contexts,
            "format": format_,
            "base_template": self.base_template,
            "active_tab": "config-context",
        }


#
# Config context schemas
#

# TODO(Glenn): disallow (or at least warn) user from manually editing config context schemas that
# have an associated owner, such as a Git repository


class ConfigContextSchemaListView(generic.ObjectListView):
    queryset = ConfigContextSchema.objects.all()
    filterset = filters.ConfigContextSchemaFilterSet
    filterset_form = forms.ConfigContextSchemaFilterForm
    table = tables.ConfigContextSchemaTable
    action_buttons = ("add",)


class ConfigContextSchemaView(generic.ObjectView):
    queryset = ConfigContextSchema.objects.all()

    def get_extra_context(self, request, instance):
        # Determine user's preferred output format
        if request.GET.get("format") in ["json", "yaml"]:
            format_ = request.GET.get("format")
            if request.user.is_authenticated:
                request.user.set_config("extras.configcontextschema.format", format_, commit=True)
        elif request.user.is_authenticated:
            format_ = request.user.get_config("extras.configcontextschema.format", "json")
        else:
            format_ = "json"

        return {
            "format": format_,
        }


class ConfigContextSchemaObjectValidationView(generic.ObjectView):
    """
    This view renders a detail tab that shows tables of objects that utilize the given schema object
    and their validation state.
    """

    queryset = ConfigContextSchema.objects.all()
    template_name = "extras/configcontextschema_validation.html"

    def get_extra_context(self, request, instance):
        """
        Reuse the model tables for config context, device, and virtual machine but inject
        the `ConfigContextSchemaValidationStateColumn` and an object edit action button.
        """
        # Prep the validator with the schema so it can be reused for all records
        validator = Draft7Validator(instance.data_schema)

        # Config context table
        config_context_table = tables.ConfigContextTable(
            data=instance.config_contexts.all(),
            orderable=False,
            extra_columns=[
                (
                    "validation_state",
                    tables.ConfigContextSchemaValidationStateColumn(validator, "data", empty_values=()),
                ),
                ("actions", ButtonsColumn(model=ConfigContext, buttons=["edit"])),
            ],
        )
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(config_context_table)

        # Device table
        device_table = DeviceTable(
            data=instance.devices.all(),
            orderable=False,
            extra_columns=[
                (
                    "validation_state",
                    tables.ConfigContextSchemaValidationStateColumn(
                        validator, "local_config_context_data", empty_values=()
                    ),
                ),
                ("actions", ButtonsColumn(model=Device, buttons=["edit"])),
            ],
        )
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(device_table)

        # Virtual machine table
        virtual_machine_table = VirtualMachineTable(
            data=instance.virtual_machines.all(),
            orderable=False,
            extra_columns=[
                (
                    "validation_state",
                    tables.ConfigContextSchemaValidationStateColumn(
                        validator, "local_config_context_data", empty_values=()
                    ),
                ),
                ("actions", ButtonsColumn(model=VirtualMachine, buttons=["edit"])),
            ],
        )
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(virtual_machine_table)

        return {
            "config_context_table": config_context_table,
            "device_table": device_table,
            "virtual_machine_table": virtual_machine_table,
            "active_tab": "validation",
        }


class ConfigContextSchemaEditView(generic.ObjectEditView):
    queryset = ConfigContextSchema.objects.all()
    model_form = forms.ConfigContextSchemaForm
    template_name = "extras/configcontextschema_edit.html"


class ConfigContextSchemaBulkEditView(generic.BulkEditView):
    queryset = ConfigContextSchema.objects.all()
    filterset = filters.ConfigContextSchemaFilterSet
    table = tables.ConfigContextSchemaTable
    form = forms.ConfigContextSchemaBulkEditForm


class ConfigContextSchemaDeleteView(generic.ObjectDeleteView):
    queryset = ConfigContextSchema.objects.all()


class ConfigContextSchemaBulkDeleteView(generic.BulkDeleteView):
    queryset = ConfigContextSchema.objects.all()
    table = tables.ConfigContextSchemaTable
    filterset = filters.ConfigContextSchemaFilterSet


#
# Contacts
#


class ContactUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.ContactBulkEditForm
    filterset_class = filters.ContactFilterSet
    filterset_form_class = forms.ContactFilterForm
    form_class = forms.ContactForm
    queryset = Contact.objects.all()
    serializer_class = serializers.ContactSerializer
    table_class = tables.ContactTable
    is_contact_associatable_model = False

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            teams = instance.teams.restrict(request.user, "view")
            teams_table = tables.TeamTable(teams, orderable=False)
            teams_table.columns.hide("actions")
            paginate = {"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
            RequestConfig(request, paginate).configure(teams_table)
            context["teams_table"] = teams_table

            # TODO: need some consistent ordering of contact_associations
            associations = instance.contact_associations.restrict(request.user, "view")
            associations_table = tables.ContactAssociationTable(associations, orderable=False)
            RequestConfig(request, paginate).configure(associations_table)
            context["contact_associations_table"] = associations_table
        return context


class ContactAssociationUIViewSet(
    ObjectBulkDestroyViewMixin,
    ObjectBulkUpdateViewMixin,
    ObjectDestroyViewMixin,
    ObjectEditViewMixin,
):
    bulk_update_form_class = forms.ContactAssociationBulkEditForm
    form_class = forms.ContactAssociationForm
    filterset_class = filters.ContactAssociationFilterSet
    queryset = ContactAssociation.objects.all()
    serializer_class = serializers.ContactAssociationSerializer
    table_class = AssociatedContactsTable
    non_filter_params = ("export", "page", "per_page", "sort")


class ObjectNewContactView(generic.ObjectEditView):
    queryset = Contact.objects.all()
    model_form = forms.ObjectNewContactForm
    template_name = "extras/object_new_contact.html"

    def post(self, request, *args, **kwargs):
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

                if hasattr(form, "save_note") and callable(form.save_note):
                    form.save_note(instance=obj, user=request.user)

                association = ContactAssociation(
                    contact=obj,
                    associated_object_type=ContentType.objects.get(id=request.POST.get("associated_object_type")),
                    associated_object_id=request.POST.get("associated_object_id"),
                    status=Status.objects.get(id=request.POST.get("status")),
                    role=Role.objects.get(id=request.POST.get("role")) if request.POST.get("role") else None,
                )
                association.validated_save()
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


class ObjectNewTeamView(generic.ObjectEditView):
    queryset = Team.objects.all()
    model_form = forms.ObjectNewTeamForm
    template_name = "extras/object_new_team.html"

    def post(self, request, *args, **kwargs):
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

                if hasattr(form, "save_note") and callable(form.save_note):
                    form.save_note(instance=obj, user=request.user)

                association = ContactAssociation(
                    team=obj,
                    associated_object_type=ContentType.objects.get(id=request.POST.get("associated_object_type")),
                    associated_object_id=request.POST.get("associated_object_id"),
                    status=Status.objects.get(id=request.POST.get("status")),
                    role=Role.objects.get(id=request.POST.get("role")) if request.POST.get("role") else None,
                )
                association.validated_save()
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


class ObjectAssignContactOrTeamView(generic.ObjectEditView):
    queryset = ContactAssociation.objects.all()
    model_form = forms.ContactAssociationForm
    template_name = "extras/object_assign_contact_or_team.html"


#
# Custom fields
#


class CustomFieldListView(generic.ObjectListView):
    queryset = CustomField.objects.all()
    table = tables.CustomFieldTable
    filterset = filters.CustomFieldFilterSet
    action_buttons = ("add",)


class CustomFieldView(generic.ObjectView):
    queryset = CustomField.objects.all()


class CustomFieldEditView(generic.ObjectEditView):
    queryset = CustomField.objects.all()
    model_form = forms.CustomFieldForm
    template_name = "extras/customfield_edit.html"

    def get_extra_context(self, request, instance):
        ctx = super().get_extra_context(request, instance)

        if request.POST:
            ctx["choices"] = forms.CustomFieldChoiceFormSet(data=request.POST, instance=instance)
        else:
            ctx["choices"] = forms.CustomFieldChoiceFormSet(instance=instance)

        return ctx

    def post(self, request, *args, **kwargs):
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

                    # ---> BEGIN difference from ObjectEditView.post()
                    # Process the formsets for choices
                    ctx = self.get_extra_context(request, obj)
                    choices = ctx["choices"]
                    if choices.is_valid():
                        choices.save()
                    else:
                        raise RuntimeError(choices.errors)
                    # <--- END difference from ObjectEditView.post()
                verb = "Created" if object_created else "Modified"
                msg = f"{verb} {self.queryset.model._meta.verbose_name}"
                logger.info(f"{msg} {obj} (PK: {obj.pk})")
                try:
                    msg = format_html('{} <a href="{}">{}</a>', msg, obj.get_absolute_url(), obj)
                except AttributeError:
                    msg = format_html("{} {}", msg, obj)
                messages.success(request, msg)

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
            # ---> BEGIN difference from ObjectEditView.post()
            except RuntimeError:
                msg = "Errors encountered when saving custom field choices. See below."
                logger.debug(msg)
                form.add_error(None, msg)
            except ProtectedError as err:
                # e.g. Trying to delete a choice that is in use.
                err_msg = err.args[0]
                protected_obj = err.protected_objects[0]
                msg = f"{protected_obj.value}: {err_msg} Please cancel this edit and start again."
                logger.debug(msg)
                form.add_error(None, msg)
            # <--- END difference from ObjectEditView.post()

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


class CustomFieldDeleteView(generic.ObjectDeleteView):
    queryset = CustomField.objects.all()


class CustomFieldBulkDeleteView(generic.BulkDeleteView):
    queryset = CustomField.objects.all()
    table = tables.CustomFieldTable
    filterset = filters.CustomFieldFilterSet

    def construct_custom_field_delete_tasks(self, queryset):
        """
        Helper method to construct a list of celery tasks to execute when bulk deleting custom fields.
        """
        tasks = [
            delete_custom_field_data.si(obj.key, set(obj.content_types.values_list("pk", flat=True)))
            for obj in queryset
        ]
        return tasks

    def perform_pre_delete(self, request, queryset):
        """
        Remove all Custom Field Keys/Values from _custom_field_data of the related ContentType in the background.
        """
        if not get_worker_count():
            messages.error(
                request, "Celery worker process not running. Object custom fields may fail to reflect this deletion."
            )
            return
        tasks = self.construct_custom_field_delete_tasks(queryset)
        # Executing the tasks in the background sequentially using chain() aligns with how a single
        # CustomField object is deleted.  We decided to not check the result because it needs at least one worker
        # to be active and comes with extra performance penalty.
        chain(*tasks).apply_async()


#
# Custom Links
#


class CustomLinkListView(generic.ObjectListView):
    queryset = CustomLink.objects.all()
    table = tables.CustomLinkTable
    filterset = filters.CustomLinkFilterSet
    filterset_form = forms.CustomLinkFilterForm
    action_buttons = ("add",)


class CustomLinkView(generic.ObjectView):
    queryset = CustomLink.objects.all()


class CustomLinkEditView(generic.ObjectEditView):
    queryset = CustomLink.objects.all()
    model_form = forms.CustomLinkForm


class CustomLinkDeleteView(generic.ObjectDeleteView):
    queryset = CustomLink.objects.all()


class CustomLinkBulkDeleteView(generic.BulkDeleteView):
    queryset = CustomLink.objects.all()
    table = tables.CustomLinkTable


#
# Dynamic Groups
#


class DynamicGroupListView(generic.ObjectListView):
    queryset = DynamicGroup.objects.all()
    table = tables.DynamicGroupTable
    filterset = filters.DynamicGroupFilterSet
    filterset_form = forms.DynamicGroupFilterForm
    action_buttons = ("add",)


class DynamicGroupView(generic.ObjectView):
    queryset = DynamicGroup.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        model = instance.content_type.model_class()
        table_class = get_table_for_model(model)

        if table_class is not None:
            # Members table (for display on Members nav tab)
            members_table = table_class(instance.members, orderable=False)
            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(members_table)

            # Descendants table
            descendants_memberships = instance.membership_tree()
            descendants_table = tables.NestedDynamicGroupDescendantsTable(
                descendants_memberships,
                orderable=False,
            )
            descendants_tree = {m.pk: m.depth for m in descendants_memberships}

            # Ancestors table
            ancestors = instance.get_ancestors()
            ancestors_table = tables.NestedDynamicGroupAncestorsTable(ancestors, orderable=False)
            ancestors_tree = instance.flatten_ancestors_tree(instance.ancestors_tree())

            context["raw_query"] = pretty_print_query(instance.generate_query())
            context["members_table"] = members_table
            context["ancestors_table"] = ancestors_table
            context["ancestors_tree"] = ancestors_tree
            context["descendants_table"] = descendants_table
            context["descendants_tree"] = descendants_tree

        return context


class DynamicGroupEditView(generic.ObjectEditView):
    queryset = DynamicGroup.objects.all()
    model_form = forms.DynamicGroupForm
    template_name = "extras/dynamicgroup_edit.html"

    def get_extra_context(self, request, instance):
        ctx = super().get_extra_context(request, instance)

        filterform_class = instance.generate_filter_form()

        if filterform_class is None:
            filter_form = None
        elif request.POST:
            filter_form = filterform_class(data=request.POST)
        else:
            initial = instance.get_initial()
            filter_form = filterform_class(initial=initial)

        ctx["filter_form"] = filter_form

        formset_kwargs = {"instance": instance}
        if request.POST:
            formset_kwargs["data"] = request.POST

        ctx["children"] = forms.DynamicGroupMembershipFormSet(**formset_kwargs)

        return ctx

    def post(self, request, *args, **kwargs):
        obj = self.alter_obj(self.get_object(kwargs), request, args, kwargs)
        form = self.model_form(data=request.POST, files=request.FILES, instance=obj)
        restrict_form_fields(form, request.user)

        if form.is_valid():
            logger.debug("Form validation was successful")

            try:
                with transaction.atomic():
                    object_created = not form.instance.present_in_database
                    # Obtain the instance, but do not yet `save()` it to the database.
                    obj = form.save(commit=False)

                    # Process the filter form and save the query filters to `obj.filter`.
                    ctx = self.get_extra_context(request, obj)
                    filter_form = ctx["filter_form"]
                    if filter_form.is_valid():
                        obj.set_filter(filter_form.cleaned_data)
                    else:
                        raise RuntimeError(filter_form.errors)

                    # After filters have been set, now we save the object to the database.
                    obj.save()
                    # Check that the new object conforms with any assigned object-level permissions
                    self.queryset.get(pk=obj.pk)

                    # Process the formsets for children
                    children = ctx["children"]
                    if children.is_valid():
                        children.save()
                    else:
                        raise RuntimeError(children.errors)
                verb = "Created" if object_created else "Modified"
                msg = f"{verb} {self.queryset.model._meta.verbose_name}"
                logger.info(f"{msg} {obj} (PK: {obj.pk})")
                try:
                    msg = format_html('{} <a href="{}">{}</a>', msg, obj.get_absolute_url(), obj)
                except AttributeError:
                    msg = format_html("{} {}", msg, obj)
                messages.success(request, msg)

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
                msg = "Object save failed due to object-level permissions violation."
                logger.debug(msg)
                form.add_error(None, msg)
            except RuntimeError:
                msg = "Errors encountered when saving Dynamic Group associations. See below."
                logger.debug(msg)
                form.add_error(None, msg)
            except ProtectedError as err:
                # e.g. Trying to delete a something that is in use.
                err_msg = err.args[0]
                protected_obj = err.protected_objects[0]
                msg = f"{protected_obj.value}: {err_msg} Please cancel this edit and start again."
                logger.debug(msg)
                form.add_error(None, msg)
            except ValidationError as err:
                msg = "Invalid filter detected in existing DynamicGroup filter data."
                logger.debug(msg)
                err_messages = err.args[0].split("\n")
                for message in err_messages:
                    if message:
                        form.add_error(None, message)

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


class DynamicGroupDeleteView(generic.ObjectDeleteView):
    queryset = DynamicGroup.objects.all()


class DynamicGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = DynamicGroup.objects.all()
    table = tables.DynamicGroupTable
    filterset = filters.DynamicGroupFilterSet


class ObjectDynamicGroupsView(View):
    """
    Present a list of dynamic groups associated to a particular object.
    base_template: The name of the template to extend. If not provided, "<app>/<model>.html" will be used.
    """

    base_template = None

    def get(self, request, model, **kwargs):
        # Handle QuerySet restriction of parent object if needed
        if hasattr(model.objects, "restrict"):
            obj = get_object_or_404(model.objects.restrict(request.user, "view"), **kwargs)
        else:
            obj = get_object_or_404(model, **kwargs)

        # Gather all dynamic groups for this object (and its related objects)
        dynamicsgroups_table = tables.DynamicGroupTable(data=obj.dynamic_groups_cached, orderable=False)

        # Apply the request context
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(dynamicsgroups_table)

        self.base_template = get_base_template(self.base_template, model)

        return render(
            request,
            "extras/object_dynamicgroups.html",
            {
                "object": obj,
                "verbose_name": obj._meta.verbose_name,
                "verbose_name_plural": obj._meta.verbose_name_plural,
                "table": dynamicsgroups_table,
                "base_template": self.base_template,
                "active_tab": "dynamic-groups",
            },
        )


#
# Export Templates
#


class ExportTemplateListView(generic.ObjectListView):
    queryset = ExportTemplate.objects.all()
    table = tables.ExportTemplateTable
    filterset = filters.ExportTemplateFilterSet
    filterset_form = forms.ExportTemplateFilterForm
    action_buttons = ("add",)


class ExportTemplateView(generic.ObjectView):
    queryset = ExportTemplate.objects.all()


class ExportTemplateEditView(generic.ObjectEditView):
    queryset = ExportTemplate.objects.all()
    model_form = forms.ExportTemplateForm


class ExportTemplateDeleteView(generic.ObjectDeleteView):
    queryset = ExportTemplate.objects.all()


class ExportTemplateBulkDeleteView(generic.BulkDeleteView):
    queryset = ExportTemplate.objects.all()
    table = tables.ExportTemplateTable


#
# External integrations
#


class ExternalIntegrationUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.ExternalIntegrationBulkEditForm
    filterset_class = filters.ExternalIntegrationFilterSet
    form_class = forms.ExternalIntegrationForm
    queryset = ExternalIntegration.objects.select_related("secrets_group")
    serializer_class = serializers.ExternalIntegrationSerializer
    table_class = tables.ExternalIntegrationTable


#
# Git repositories
#


class GitRepositoryListView(generic.ObjectListView):
    queryset = GitRepository.objects.all()
    filterset = filters.GitRepositoryFilterSet
    filterset_form = forms.GitRepositoryFilterForm
    table = tables.GitRepositoryTable
    template_name = "extras/gitrepository_list.html"

    def extra_context(self):
        # Get the newest results for each repository name
        results = {
            r.task_kwargs["repository"]: r
            for r in JobResult.objects.filter(
                task_name__startswith="nautobot.core.jobs.GitRepository",
                task_kwargs__repository__isnull=False,
                status__in=JobResultStatusChoices.READY_STATES,
            )
            .order_by("date_done")
            .defer("result")
        }
        return {
            "job_results": results,
            "datasource_contents": get_datasource_contents("extras.gitrepository"),
        }


class GitRepositoryView(generic.ObjectView):
    queryset = GitRepository.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "datasource_contents": get_datasource_contents("extras.gitrepository"),
        }


class GitRepositoryEditView(generic.ObjectEditView):
    queryset = GitRepository.objects.all()
    model_form = forms.GitRepositoryForm
    template_name = "extras/gitrepository_object_edit.html"

    # TODO(jathan): Align with changes for v2 where we're not stashing the user on the instance for
    # magical calls and instead discretely calling `repo.sync(user=user, dry_run=dry_run)`, but
    # again, this will be moved to the API calls, so just something to keep in mind.
    def alter_obj(self, obj, request, url_args, url_kwargs):
        # A GitRepository needs to know the originating request when it's saved so that it can enqueue using it
        obj.user = request.user
        return super().alter_obj(obj, request, url_args, url_kwargs)

    def get_return_url(self, request, obj):
        if request.method == "POST":
            return reverse("extras:gitrepository_result", kwargs={"pk": obj.pk})
        return super().get_return_url(request, obj)


class GitRepositoryDeleteView(generic.ObjectDeleteView):
    queryset = GitRepository.objects.all()


class GitRepositoryBulkImportView(generic.BulkImportView):  # 3.0 TODO: remove, unused
    queryset = GitRepository.objects.all()
    table = tables.GitRepositoryBulkTable


class GitRepositoryBulkEditView(generic.BulkEditView):
    queryset = GitRepository.objects.select_related("secrets_group")
    filterset = filters.GitRepositoryFilterSet
    table = tables.GitRepositoryBulkTable
    form = forms.GitRepositoryBulkEditForm

    def alter_obj(self, obj, request, url_args, url_kwargs):
        # A GitRepository needs to know the originating request when it's saved so that it can enqueue using it
        obj.request = request
        return super().alter_obj(obj, request, url_args, url_kwargs)

    def extra_context(self):
        return {
            "datasource_contents": get_datasource_contents("extras.gitrepository"),
        }


class GitRepositoryBulkDeleteView(generic.BulkDeleteView):
    queryset = GitRepository.objects.all()
    table = tables.GitRepositoryBulkTable
    filterset = filters.GitRepositoryFilterSet

    def extra_context(self):
        return {
            "datasource_contents": get_datasource_contents("extras.gitrepository"),
        }


def check_and_call_git_repository_function(request, pk, func):
    """Helper for checking Git permissions and worker availability, then calling provided function if all is well
    Args:
        request (HttpRequest): request object.
        pk (UUID): GitRepository pk value.
        func (function): Enqueue git repo function.
    Returns:
        (Union[HttpResponseForbidden,redirect]): HttpResponseForbidden if user does not have permission to run the job,
            otherwise redirect to the job result page.
    """
    if not request.user.has_perm("extras.change_gitrepository"):
        return HttpResponseForbidden()

    # Allow execution only if a worker process is running.
    if not get_worker_count():
        messages.error(request, "Unable to run job: Celery worker process not running.")
        return redirect(request.get_full_path(), permanent=False)
    else:
        repository = get_object_or_404(GitRepository, pk=pk)
        job_result = func(repository, request.user)

    return redirect(job_result.get_absolute_url())


class GitRepositorySyncView(View):
    def post(self, request, pk):
        return check_and_call_git_repository_function(request, pk, enqueue_pull_git_repository_and_refresh_data)


class GitRepositoryDryRunView(View):
    def post(self, request, pk):
        return check_and_call_git_repository_function(request, pk, enqueue_git_repository_diff_origin_and_local)


class GitRepositoryResultView(generic.ObjectView):
    """
    Display a JobResult and its Job data.
    """

    queryset = GitRepository.objects.all()
    template_name = "extras/gitrepository_result.html"

    def get_required_permission(self):
        return "extras.view_gitrepository"

    def get_extra_context(self, request, instance):
        job_result = instance.get_latest_sync()

        return {
            "result": job_result,
            "base_template": "extras/gitrepository.html",
            "object": instance,
            "active_tab": "result",
        }


#
# Saved GraphQL queries
#


class GraphQLQueryListView(generic.ObjectListView):
    queryset = GraphQLQuery.objects.all()
    table = tables.GraphQLQueryTable
    filterset = filters.GraphQLQueryFilterSet
    filterset_form = forms.GraphQLQueryFilterForm
    action_buttons = ("add",)


class GraphQLQueryView(generic.ObjectView):
    queryset = GraphQLQuery.objects.all()


class GraphQLQueryEditView(generic.ObjectEditView):
    queryset = GraphQLQuery.objects.all()
    model_form = forms.GraphQLQueryForm


class GraphQLQueryDeleteView(generic.ObjectDeleteView):
    queryset = GraphQLQuery.objects.all()


class GraphQLQueryBulkDeleteView(generic.BulkDeleteView):
    queryset = GraphQLQuery.objects.all()
    table = tables.GraphQLQueryTable


#
# Image attachments
#


class ImageAttachmentEditView(generic.ObjectEditView):
    """
    View for creating and editing ImageAttachments.

    Note that a URL kwargs parameter of "pk" identifies an existing ImageAttachment to edit,
    while kwargs of "object_id" or "slug" identify the parent model instance to attach an ImageAttachment to.
    """

    queryset = ImageAttachment.objects.all()
    model_form = forms.ImageAttachmentForm

    def get_object(self, kwargs):
        if "pk" in kwargs:
            return get_object_or_404(self.queryset, pk=kwargs["pk"])
        return self.queryset.model()

    def alter_obj(self, imageattachment, request, args, kwargs):
        if not imageattachment.present_in_database:
            # Assign the parent object based on URL kwargs
            model = kwargs.get("model")
            if "object_id" in kwargs:
                imageattachment.parent = get_object_or_404(model, pk=kwargs["object_id"])
            elif "slug" in kwargs:
                imageattachment.parent = get_object_or_404(model, slug=kwargs["slug"])
            else:
                raise RuntimeError("Neither object_id nor slug were provided?")
        return imageattachment

    def get_return_url(self, request, imageattachment):
        return imageattachment.parent.get_absolute_url()


class ImageAttachmentDeleteView(generic.ObjectDeleteView):
    queryset = ImageAttachment.objects.all()

    def get_return_url(self, request, imageattachment):
        return imageattachment.parent.get_absolute_url()


#
# Jobs
#


class JobListView(generic.ObjectListView):
    """
    Retrieve all of the available jobs from disk and the recorded JobResult (if any) for each.
    """

    queryset = JobModel.objects.all()
    table = tables.JobTable
    filterset = filters.JobFilterSet
    filterset_form = forms.JobFilterForm
    action_buttons = ()
    non_filter_params = ("display",)
    template_name = "extras/job_list.html"

    def alter_queryset(self, request):
        queryset = super().alter_queryset(request)
        # Default to hiding "hidden" and non-installed jobs
        if "hidden" not in request.GET:
            queryset = queryset.filter(hidden=False)
        if "installed" not in request.GET:
            queryset = queryset.filter(installed=True)
        return queryset

    def extra_context(self):
        # Determine user's preferred display
        if self.request.GET.get("display") in ["list", "tiles"]:
            display = self.request.GET.get("display")
            if self.request.user.is_authenticated:
                self.request.user.set_config("extras.job.display", display, commit=True)
        elif self.request.user.is_authenticated:
            display = self.request.user.get_config("extras.job.display", "list")
        else:
            display = "list"

        return {
            "table_inc_template": "extras/inc/job_tiles.html" if display == "tiles" else "extras/inc/job_table.html",
            "display": display,
        }


class JobRunView(ObjectPermissionRequiredMixin, View):
    """
    View the parameters of a Job and enqueue it if desired.
    """

    queryset = JobModel.objects.all()

    def get_required_permission(self):
        return "extras.run_job"

    def _get_job_model_or_404(self, class_path=None, pk=None):
        """Helper function for get() and post()."""
        if class_path:
            try:
                job_model = self.queryset.get_for_class_path(class_path)
            except JobModel.DoesNotExist:
                raise Http404
        else:
            job_model = get_object_or_404(self.queryset, pk=pk)

        return job_model

    def get(self, request, class_path=None, pk=None):
        job_model = self._get_job_model_or_404(class_path, pk)

        try:
            try:
                job_class = job_model.job_class
            except TypeError as exc:
                # job_class may be None
                raise RuntimeError("Job code for this job is not currently installed or loadable") from exc
            initial = normalize_querydict(request.GET, form_class=job_class.as_form_class())
            if "kwargs_from_job_result" in initial:
                job_result_pk = initial.pop("kwargs_from_job_result")
                try:
                    job_result = job_model.job_results.get(pk=job_result_pk)
                    # Allow explicitly specified arg values in request.GET to take precedence over the saved task_kwargs,
                    # for example "?kwargs_from_job_result=<UUID>&integervar=22"
                    explicit_initial = initial
                    initial = job_result.task_kwargs.copy()
                    task_queue = job_result.celery_kwargs.get("queue", None)
                    if task_queue is not None:
                        initial["_task_queue"] = task_queue
                    initial["_profile"] = job_result.celery_kwargs.get("nautobot_job_profile", False)
                    initial.update(explicit_initial)
                except JobResult.DoesNotExist:
                    messages.warning(
                        request,
                        f"JobResult {job_result_pk} not found, cannot use it to pre-populate inputs.",
                    )

            template_name = "extras/job.html"
            job_form = job_class.as_form(initial=initial)
            if hasattr(job_class, "template_name"):
                try:
                    get_template(job_class.template_name)
                    template_name = job_class.template_name
                except TemplateDoesNotExist as err:
                    messages.error(request, f'Unable to render requested custom job template "{template_name}": {err}')
        except RuntimeError as err:
            messages.error(request, f"Unable to run or schedule '{job_model}': {err}")
            return redirect("extras:job_list")

        schedule_form = forms.JobScheduleForm(initial=initial)

        return render(
            request,
            template_name,  # 2.0 TODO: extras/job_submission.html
            {
                "job_model": job_model,
                "job_form": job_form,
                "schedule_form": schedule_form,
            },
        )

    def post(self, request, class_path=None, pk=None):
        job_model = self._get_job_model_or_404(class_path, pk)

        job_form = job_model.job_class.as_form(request.POST, request.FILES) if job_model.job_class is not None else None
        schedule_form = forms.JobScheduleForm(request.POST)
        task_queue = request.POST.get("_task_queue")

        return_url = request.POST.get("_return_url")
        if return_url is not None and url_has_allowed_host_and_scheme(url=return_url, allowed_hosts=request.get_host()):
            return_url = iri_to_uri(return_url)
        else:
            return_url = None

        # Allow execution only if a worker process is running and the job is runnable.
        if not get_worker_count(queue=task_queue):
            messages.error(request, "Unable to run or schedule job: Celery worker process not running.")
        elif not job_model.installed or job_model.job_class is None:
            messages.error(request, "Unable to run or schedule job: Job is not presently installed.")
        elif not job_model.enabled:
            messages.error(request, "Unable to run or schedule job: Job is not enabled to be run.")
        elif (
            job_model.has_sensitive_variables
            and request.POST.get("_schedule_type") != JobExecutionType.TYPE_IMMEDIATELY
        ):
            messages.error(request, "Unable to schedule job: Job may have sensitive input variables.")
        elif job_model.has_sensitive_variables and job_model.approval_required:
            messages.error(
                request,
                "Unable to run or schedule job: "
                "This job is flagged as possibly having sensitive variables but is also flagged as requiring approval."
                "One of these two flags must be removed before this job can be scheduled or run.",
            )
        elif job_form is not None and job_form.is_valid() and schedule_form.is_valid():
            task_queue = job_form.cleaned_data.pop("_task_queue", None)
            dryrun = job_form.cleaned_data.get("dryrun", False)
            # Run the job. A new JobResult is created.
            profile = job_form.cleaned_data.pop("_profile")
            schedule_type = schedule_form.cleaned_data["_schedule_type"]

            if (not dryrun and job_model.approval_required) or schedule_type in JobExecutionType.SCHEDULE_CHOICES:
                crontab = ""

                if schedule_type == JobExecutionType.TYPE_IMMEDIATELY:
                    # The job must be approved.
                    # If the schedule_type is immediate, we still create the task, but mark it for approval
                    # as a once in the future task with the due date set to the current time. This means
                    # when approval is granted, the task is immediately due for execution.
                    schedule_type = JobExecutionType.TYPE_FUTURE
                    schedule_datetime = timezone.now()
                    schedule_name = f"{job_model} - {schedule_datetime}"

                else:
                    schedule_name = schedule_form.cleaned_data["_schedule_name"]

                    if schedule_type == JobExecutionType.TYPE_CUSTOM:
                        crontab = schedule_form.cleaned_data["_recurrence_custom_time"]
                        # doing .get("key", "default") returns None instead of "default" here for some reason
                        schedule_datetime = schedule_form.cleaned_data.get("_schedule_start_time")
                        if schedule_datetime is None:
                            # "_schedule_start_time" is checked against ScheduledJob.earliest_possible_time()
                            # which returns timezone.now() + timedelta(seconds=15)
                            schedule_datetime = timezone.now() + timedelta(seconds=20)
                    else:
                        schedule_datetime = schedule_form.cleaned_data["_schedule_start_time"]

                celery_kwargs = {"nautobot_job_profile": profile, "queue": task_queue}
                scheduled_job = ScheduledJob(
                    name=schedule_name,
                    task=job_model.job_class.registered_name,
                    job_model=job_model,
                    start_time=schedule_datetime,
                    description=f"Nautobot job {schedule_name} scheduled by {request.user} for {schedule_datetime}",
                    kwargs=job_model.job_class.serialize_data(job_form.cleaned_data),
                    celery_kwargs=celery_kwargs,
                    interval=schedule_type,
                    one_off=schedule_type == JobExecutionType.TYPE_FUTURE,
                    queue=task_queue,
                    user=request.user,
                    approval_required=job_model.approval_required,
                    crontab=crontab,
                )
                scheduled_job.validated_save()

                if job_model.approval_required:
                    messages.success(request, f"Job {schedule_name} successfully submitted for approval")
                    return redirect(return_url if return_url else "extras:scheduledjob_approval_queue_list")
                else:
                    messages.success(request, f"Job {schedule_name} successfully scheduled")
                    return redirect(return_url if return_url else "extras:scheduledjob_list")

            else:
                # Enqueue job for immediate execution
                job_kwargs = job_model.job_class.prepare_job_kwargs(job_form.cleaned_data)
                job_result = JobResult.enqueue_job(
                    job_model,
                    request.user,
                    profile=profile,
                    task_queue=task_queue,
                    **job_model.job_class.serialize_data(job_kwargs),
                )

                if return_url:
                    messages.info(
                        request,
                        format_html(
                            'Job enqueued. <a href="{}">Click here for the results.</a>',
                            job_result.get_absolute_url(),
                        ),
                    )
                    return redirect(return_url)

                return redirect("extras:jobresult", pk=job_result.pk)

        if return_url:
            return redirect(return_url)

        template_name = "extras/job.html"
        if job_model.job_class is not None and hasattr(job_model.job_class, "template_name"):
            try:
                get_template(job_model.job_class.template_name)
                template_name = job_model.job_class.template_name
            except TemplateDoesNotExist as err:
                messages.error(request, f'Unable to render requested custom job template "{template_name}": {err}')

        return render(
            request,
            template_name,
            {
                "job_model": job_model,
                "job_form": job_form,
                "schedule_form": schedule_form,
            },
        )


class JobView(generic.ObjectView):
    queryset = JobModel.objects.all()
    template_name = "extras/job_detail.html"


class JobEditView(generic.ObjectEditView):
    queryset = JobModel.objects.all()
    model_form = forms.JobEditForm
    template_name = "extras/job_edit.html"


class JobBulkEditView(generic.BulkEditView):
    queryset = JobModel.objects.all()
    filterset = filters.JobFilterSet
    table = tables.JobTable
    form = forms.JobBulkEditForm
    template_name = "extras/job_bulk_edit.html"

    def extra_post_save_action(self, obj, form):
        cleaned_data = form.cleaned_data

        # Handle text related fields
        for overridable_field in JOB_OVERRIDABLE_FIELDS:
            override_field = overridable_field + "_override"
            clear_override_field = "clear_" + overridable_field + "_override"
            reset_override = cleaned_data.get(clear_override_field, False)
            override_value = cleaned_data.get(overridable_field)
            if reset_override:
                setattr(obj, override_field, False)
            elif not reset_override and override_value not in [None, ""]:
                setattr(obj, override_field, True)
                setattr(obj, overridable_field, override_value)

        obj.validated_save()


class JobDeleteView(generic.ObjectDeleteView):
    queryset = JobModel.objects.all()


class JobBulkDeleteView(generic.BulkDeleteView):
    queryset = JobModel.objects.all()
    filterset = filters.JobFilterSet
    table = tables.JobTable


class JobApprovalRequestView(generic.ObjectView):
    """
    This view handles requests to view and approve a Job execution request.
    It renders the Job's form in much the same way as `JobView` except all
    form fields are disabled and actions on the form relate to approval of the
    job's execution, rather than initial job form input.
    """

    queryset = ScheduledJob.objects.needs_approved()
    template_name = "extras/job_approval_request.html"
    additional_permissions = ("extras.view_job",)

    def get_extra_context(self, request, instance):
        """
        Render the job form with data from the scheduled_job instance, but mark all fields as disabled.
        We don't care to actually get any data back from the form as we will not ever change it.
        Instead, we offer the user three submit buttons, dry-run, approve, and deny, which we act upon in the post.
        """
        job_model = instance.job_model
        if job_model is not None:
            job_class = job_model.job_class
        else:
            # 2.0 TODO: remove this fallback?
            job_class = get_job(instance.job_class)

        if job_class is not None:
            # Render the form with all fields disabled
            initial = instance.kwargs
            initial["_task_queue"] = instance.queue
            initial["_profile"] = instance.celery_kwargs.get("profile", False)
            job_form = job_class().as_form(initial=initial, approval_view=True)
        else:
            job_form = None

        return {
            "job_form": job_form,
        }

    def post(self, request, pk):
        """
        Act upon one of the 3 submit button actions from the user.

        dry-run will immediately enqueue the job with commit=False and send the user to the normal JobResult view
        deny will delete the scheduled_job instance
        approve will mark the scheduled_job as approved, allowing the schedular to schedule the job execution task
        """
        scheduled_job = get_object_or_404(ScheduledJob, pk=pk)

        post_data = request.POST

        deny = "_deny" in post_data
        approve = "_approve" in post_data
        force_approve = "_force_approve" in post_data
        dry_run = "_dry_run" in post_data

        job_model = scheduled_job.job_model

        if dry_run:
            # To dry-run a job, a user needs the same permissions that would be needed to run the job directly
            if job_model is None:
                messages.error(request, "There is no job associated with this request? Cannot run it!")
            elif not job_model.runnable:
                messages.error(request, "This job cannot be run at this time")
            elif not JobModel.objects.check_perms(self.request.user, instance=job_model, action="run"):
                messages.error(request, "You do not have permission to run this job")
            elif not job_model.supports_dryrun:
                messages.error(request, "This job does not support dryrun")
            else:
                # Immediately enqueue the job and send the user to the normal JobResult view
                job_kwargs = job_model.job_class.prepare_job_kwargs(scheduled_job.kwargs or {})
                job_kwargs["dryrun"] = True
                job_result = JobResult.enqueue_job(
                    job_model,
                    request.user,
                    celery_kwargs=scheduled_job.celery_kwargs,
                    **job_model.job_class.serialize_data(job_kwargs),
                )

                return redirect("extras:jobresult", pk=job_result.pk)
        elif deny:
            if not (
                self.queryset.check_perms(request.user, instance=scheduled_job, action="delete")
                and job_model is not None
                and JobModel.objects.check_perms(request.user, instance=job_model, action="approve")
            ):
                messages.error(request, "You do not have permission to deny this request.")
            else:
                # Delete the scheduled_job instance
                scheduled_job.delete()
                if request.user == scheduled_job.user:
                    messages.error(request, f"Approval request for {scheduled_job.name} was revoked")
                else:
                    messages.error(request, f"Approval of {scheduled_job.name} was denied")

                return redirect("extras:scheduledjob_approval_queue_list")

        elif approve or force_approve:
            if job_model is None:
                messages.error(request, "There is no job associated with this request? Cannot run it!")
            elif not (
                self.queryset.check_perms(request.user, instance=scheduled_job, action="change")
                and JobModel.objects.check_perms(request.user, instance=job_model, action="approve")
            ):
                messages.error(request, "You do not have permission to approve this request.")
            elif request.user == scheduled_job.user:
                # The requestor *cannot* approve their own job
                messages.error(request, "You cannot approve your own job request!")
            else:
                # Mark the scheduled_job as approved, allowing the schedular to schedule the job execution task
                if scheduled_job.one_off and scheduled_job.start_time < timezone.now() and not force_approve:
                    return render(request, "extras/job_approval_confirmation.html", {"scheduled_job": scheduled_job})
                scheduled_job.approved_by_user = request.user
                scheduled_job.approved_at = timezone.now()
                scheduled_job.save()

                messages.success(request, f"{scheduled_job.name} was approved and will now begin execution")

                return redirect("extras:scheduledjob_approval_queue_list")

        return render(
            request,
            self.get_template_name(),
            {
                "object": scheduled_job,
                **self.get_extra_context(request, scheduled_job),
            },
        )


class ScheduledJobListView(generic.ObjectListView):
    queryset = ScheduledJob.objects.enabled()
    table = tables.ScheduledJobTable
    filterset = filters.ScheduledJobFilterSet
    filterset_form = forms.ScheduledJobFilterForm
    action_buttons = ()


class ScheduledJobBulkDeleteView(generic.BulkDeleteView):
    queryset = ScheduledJob.objects.all()
    table = tables.ScheduledJobTable
    filterset = filters.ScheduledJobFilterSet


class ScheduledJobApprovalQueueListView(generic.ObjectListView):
    queryset = ScheduledJob.objects.needs_approved()
    table = tables.ScheduledJobApprovalQueueTable
    filterset = filters.ScheduledJobFilterSet
    filterset_form = forms.ScheduledJobFilterForm
    action_buttons = ()
    template_name = "extras/scheduled_jobs_approval_queue_list.html"


class ScheduledJobView(generic.ObjectView):
    queryset = ScheduledJob.objects.all()

    def get_extra_context(self, request, instance):
        job_class = get_job(instance.task)
        labels = {}
        if job_class is not None:
            for name, var in job_class._get_vars().items():
                field = var.as_field()
                if field.label:
                    labels[name] = var
                else:
                    labels[name] = pretty_name(name)
        return {"labels": labels, "job_class_found": (job_class is not None)}


class ScheduledJobDeleteView(generic.ObjectDeleteView):
    queryset = ScheduledJob.objects.all()


#
# Job hooks
#


class JobHookListView(generic.ObjectListView):
    queryset = JobHook.objects.all()
    table = tables.JobHookTable
    filterset = filters.JobHookFilterSet
    filterset_form = forms.JobHookFilterForm
    action_buttons = ("add",)


class JobHookView(generic.ObjectView):
    queryset = JobHook.objects.all()

    def get_extra_context(self, request, instance):
        return {"content_types": instance.content_types.order_by("app_label", "model")}


class JobHookEditView(generic.ObjectEditView):
    queryset = JobHook.objects.all()
    model_form = forms.JobHookForm


class JobHookDeleteView(generic.ObjectDeleteView):
    queryset = JobHook.objects.all()


class JobHookBulkDeleteView(generic.BulkDeleteView):
    queryset = JobHook.objects.all()
    table = tables.JobHookTable


#
# JobResult
#


def get_annotated_jobresult_queryset():
    return (
        JobResult.objects.defer("result")
        .select_related("job_model", "user")
        .annotate(
            debug_log_count=count_related(
                JobLogEntry, "job_result", filter_dict={"log_level": LogLevelChoices.LOG_DEBUG}
            ),
            info_log_count=count_related(
                JobLogEntry, "job_result", filter_dict={"log_level": LogLevelChoices.LOG_INFO}
            ),
            warning_log_count=count_related(
                JobLogEntry, "job_result", filter_dict={"log_level": LogLevelChoices.LOG_WARNING}
            ),
            error_log_count=count_related(
                JobLogEntry,
                "job_result",
                filter_dict={"log_level__in": [LogLevelChoices.LOG_ERROR, LogLevelChoices.LOG_CRITICAL]},
            ),
        )
    )


class JobResultListView(generic.ObjectListView):
    """
    List JobResults
    """

    queryset = get_annotated_jobresult_queryset()
    filterset = filters.JobResultFilterSet
    filterset_form = forms.JobResultFilterForm
    table = tables.JobResultTable
    action_buttons = ()


class JobResultDeleteView(generic.ObjectDeleteView):
    queryset = JobResult.objects.all()


class JobResultBulkDeleteView(generic.BulkDeleteView):
    queryset = get_annotated_jobresult_queryset()
    table = tables.JobResultTable
    filterset = filters.JobResultFilterSet


class JobResultView(generic.ObjectView):
    """
    Display a JobResult and its Job data.
    """

    queryset = JobResult.objects.prefetch_related("job_model", "user")
    template_name = "extras/jobresult.html"

    def get_extra_context(self, request, instance):
        associated_record = None
        job_class = None
        if instance.job_model is not None:
            job_class = instance.job_model.job_class

        return {
            "job": job_class,
            "associated_record": associated_record,
            "result": instance,
        }


class JobLogEntryTableView(View):
    """
    Display a table of `JobLogEntry` objects for a given `JobResult` instance.
    """

    queryset = JobResult.objects.all()

    def get(self, request, pk=None):
        instance = self.queryset.get(pk=pk)
        filter_q = request.GET.get("q")
        if filter_q:
            queryset = instance.job_log_entries.filter(
                Q(message__icontains=filter_q) | Q(log_level__icontains=filter_q)
            )
        else:
            queryset = instance.job_log_entries.all()
        log_table = tables.JobLogEntryTable(data=queryset, user=request.user)
        RequestConfig(request).configure(log_table)
        return HttpResponse(log_table.as_html(request))


#
# Job Button
#


class JobButtonUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.JobButtonBulkEditForm
    filterset_class = filters.JobButtonFilterSet
    filterset_form_class = forms.JobButtonFilterForm
    form_class = forms.JobButtonForm
    queryset = JobButton.objects.all()
    serializer_class = serializers.JobButtonSerializer
    table_class = tables.JobButtonTable


#
# Change logging
#


class ObjectChangeListView(generic.ObjectListView):
    queryset = ObjectChange.objects.all()
    filterset = filters.ObjectChangeFilterSet
    filterset_form = forms.ObjectChangeFilterForm
    table = tables.ObjectChangeTable
    template_name = "extras/objectchange_list.html"
    action_buttons = ("export",)

    # 2.0 TODO: Remove this remapping and solve it at the `BaseFilterSet` as it is addressing a breaking change.
    def get(self, request, **kwargs):
        # Remappings below allow previous queries of time_before and time_after to use
        # newer methods specifying the lookup method.

        # They will only use the previous arguments if the newer ones are undefined

        if request.GET.get("time_after") and request.GET.get("time__gte") is None:
            request.GET._mutable = True
            request.GET.update({"time__gte": request.GET.get("time_after")})
            request.GET._mutable = False

        if request.GET.get("time_before") and request.GET.get("time__lte") is None:
            request.GET._mutable = True
            request.GET.update({"time__lte": request.GET.get("time_before")})
            request.GET._mutable = False

        return super().get(request=request, **kwargs)


class ObjectChangeView(generic.ObjectView):
    queryset = ObjectChange.objects.all()

    def get_extra_context(self, request, instance):
        related_changes = instance.get_related_changes(user=request.user).filter(request_id=instance.request_id)
        related_changes_table = tables.ObjectChangeTable(data=related_changes[:50], orderable=False)

        snapshots = instance.get_snapshots()
        return {
            "diff_added": snapshots["differences"]["added"],
            "diff_removed": snapshots["differences"]["removed"],
            "next_change": instance.get_next_change(request.user),
            "prev_change": instance.get_prev_change(request.user),
            "related_changes_table": related_changes_table,
            "related_changes_count": related_changes.count(),
        }


class ObjectChangeLogView(View):
    """
    Present a history of changes made to a particular object.
    base_template: The name of the template to extend. If not provided, "<app>/<model>.html" will be used.
    """

    base_template = None

    def get(self, request, model, **kwargs):
        # Handle QuerySet restriction of parent object if needed
        if hasattr(model.objects, "restrict"):
            obj = get_object_or_404(model.objects.restrict(request.user, "view"), **kwargs)
        else:
            obj = get_object_or_404(model, **kwargs)

        # Gather all changes for this object (and its related objects)
        content_type = ContentType.objects.get_for_model(model)
        objectchanges = (
            ObjectChange.objects.restrict(request.user, "view")
            .select_related("user", "changed_object_type")
            .filter(
                Q(changed_object_type=content_type, changed_object_id=obj.pk)
                | Q(related_object_type=content_type, related_object_id=obj.pk)
            )
        )
        objectchanges_table = tables.ObjectChangeTable(data=objectchanges, orderable=False)

        # Apply the request context
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(objectchanges_table)

        self.base_template = get_base_template(self.base_template, model)

        return render(
            request,
            "extras/object_changelog.html",
            {
                "object": obj,
                "verbose_name": obj._meta.verbose_name,
                "verbose_name_plural": obj._meta.verbose_name_plural,
                "table": objectchanges_table,
                "base_template": self.base_template,
                "active_tab": "changelog",
                # Currently only Contact and Team models are not contact_associatable.
                "is_contact_associatable_model": type(obj) not in [Contact, Team],
            },
        )


#
# Notes
#


class NoteView(generic.ObjectView):
    queryset = Note.objects.all()


class NoteListView(generic.ObjectListView):
    """
    List Notes
    """

    queryset = Note.objects.all()
    filterset = filters.NoteFilterSet
    filterset_form = forms.NoteFilterForm
    table = tables.NoteTable
    action_buttons = ()


class NoteEditView(generic.ObjectEditView):
    queryset = Note.objects.all()
    model_form = forms.NoteForm

    def alter_obj(self, obj, request, url_args, url_kwargs):
        obj.user = request.user
        return obj


class NoteDeleteView(generic.ObjectDeleteView):
    queryset = Note.objects.all()


class ObjectNotesView(View):
    """
    Present a list of notes associated to a particular object.
    base_template: The name of the template to extend. If not provided, "<app>/<model>.html" will be used.
    """

    base_template = None

    def get(self, request, model, **kwargs):
        # Handle QuerySet restriction of parent object if needed
        if hasattr(model.objects, "restrict"):
            obj = get_object_or_404(model.objects.restrict(request.user, "view"), **kwargs)
        else:
            obj = get_object_or_404(model, **kwargs)

        notes_form = forms.NoteForm(
            initial={
                "assigned_object_type": ContentType.objects.get_for_model(obj),
                "assigned_object_id": obj.pk,
            }
        )
        notes_table = tables.NoteTable(obj.notes)

        # Apply the request context
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(notes_table)

        self.base_template = get_base_template(self.base_template, model)

        return render(
            request,
            "extras/object_notes.html",
            {
                "object": obj,
                "verbose_name": obj._meta.verbose_name,
                "verbose_name_plural": obj._meta.verbose_name_plural,
                "table": notes_table,
                "base_template": self.base_template,
                "active_tab": "notes",
                "form": notes_form,
                # Currently only Contact and Team models are not contact_associatable.
                "is_contact_associatable_model": type(obj) not in [Contact, Team],
            },
        )


#
# Relationship
#


class RelationshipListView(generic.ObjectListView):
    queryset = Relationship.objects.all()
    filterset = filters.RelationshipFilterSet
    filterset_form = forms.RelationshipFilterForm
    table = tables.RelationshipTable
    action_buttons = ("add",)


class RelationshipView(generic.ObjectView):
    queryset = Relationship.objects.all()


class RelationshipEditView(generic.ObjectEditView):
    queryset = Relationship.objects.all()
    model_form = forms.RelationshipForm
    template_name = "extras/relationship_edit.html"


class RelationshipBulkDeleteView(generic.BulkDeleteView):
    queryset = Relationship.objects.all()
    table = tables.RelationshipTable
    filterset = filters.RelationshipFilterSet


class RelationshipDeleteView(generic.ObjectDeleteView):
    queryset = Relationship.objects.all()


class RelationshipAssociationListView(generic.ObjectListView):
    queryset = RelationshipAssociation.objects.all()
    filterset = filters.RelationshipAssociationFilterSet
    filterset_form = forms.RelationshipAssociationFilterForm
    table = tables.RelationshipAssociationTable
    action_buttons = ()


class RelationshipAssociationBulkDeleteView(generic.BulkDeleteView):
    queryset = RelationshipAssociation.objects.all()
    table = tables.RelationshipAssociationTable
    filterset = filters.RelationshipAssociationFilterSet


class RelationshipAssociationDeleteView(generic.ObjectDeleteView):
    queryset = RelationshipAssociation.objects.all()


#
# Roles
#


class RoleUIViewSet(viewsets.NautobotUIViewSet):
    """`Roles` UIViewSet."""

    queryset = Role.objects.all()
    bulk_update_form_class = RoleBulkEditForm
    filterset_class = RoleFilterSet
    form_class = RoleForm
    serializer_class = serializers.RoleSerializer
    table_class = RoleTable

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            context["content_types"] = instance.content_types.order_by("app_label", "model")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }

            if ContentType.objects.get_for_model(Device) in context["content_types"]:
                devices = instance.devices.select_related(
                    "status",
                    "location",
                    "tenant",
                    "role",
                    "rack",
                    "device_type",
                ).restrict(request.user, "view")
                device_table = DeviceTable(devices)
                device_table.columns.hide("role")
                RequestConfig(request, paginate).configure(device_table)
                context["device_table"] = device_table

            if ContentType.objects.get_for_model(Controller) in context["content_types"]:
                controllers = instance.controllers.select_related(
                    "status",
                    "location",
                    "tenant",
                    "role",
                ).restrict(request.user, "view")
                controller_table = ControllerTable(controllers)
                controller_table.columns.hide("role")
                RequestConfig(request, paginate).configure(controller_table)
                context["controller_table"] = controller_table

            if ContentType.objects.get_for_model(IPAddress) in context["content_types"]:
                ipaddress = (
                    instance.ip_addresses.select_related("status", "tenant")
                    .restrict(request.user, "view")
                    .annotate(
                        interface_count=count_related(Interface, "ip_addresses"),
                        interface_parent_count=count_related(Device, "interfaces__ip_addresses", distinct=True),
                        vm_interface_count=count_related(VMInterface, "ip_addresses"),
                        vm_interface_parent_count=count_related(
                            VirtualMachine, "interfaces__ip_addresses", distinct=True
                        ),
                    )
                )
                ipaddress_table = IPAddressTable(ipaddress)
                ipaddress_table.columns.hide("role")
                RequestConfig(request, paginate).configure(ipaddress_table)
                context["ipaddress_table"] = ipaddress_table

            if ContentType.objects.get_for_model(Prefix) in context["content_types"]:
                prefixes = (
                    instance.prefixes.select_related(
                        "status",
                        "tenant",
                        "vlan",
                        "namespace",
                    )
                    .restrict(request.user, "view")
                    .annotate(location_count=count_related(Location, "prefixes"))
                )
                prefix_table = PrefixTable(prefixes)
                prefix_table.columns.hide("role")
                RequestConfig(request, paginate).configure(prefix_table)
                context["prefix_table"] = prefix_table
            if ContentType.objects.get_for_model(Rack) in context["content_types"]:
                racks = instance.racks.select_related(
                    "location",
                    "status",
                    "tenant",
                    "rack_group",
                ).restrict(request.user, "view")
                rack_table = RackTable(racks)
                rack_table.columns.hide("role")
                RequestConfig(request, paginate).configure(rack_table)
                context["rack_table"] = rack_table
            if ContentType.objects.get_for_model(VirtualMachine) in context["content_types"]:
                virtual_machines = instance.virtual_machines.select_related(
                    "cluster",
                    "role",
                    "status",
                    "tenant",
                ).restrict(request.user, "view")
                virtual_machine_table = VirtualMachineTable(virtual_machines)
                virtual_machine_table.columns.hide("role")
                RequestConfig(request, paginate).configure(virtual_machine_table)
                context["virtual_machine_table"] = virtual_machine_table

            if ContentType.objects.get_for_model(VLAN) in context["content_types"]:
                vlans = (
                    instance.vlans.annotate(location_count=count_related(Location, "vlans"))
                    .select_related(
                        "vlan_group",
                        "status",
                        "tenant",
                    )
                    .restrict(request.user, "view")
                )
                vlan_table = VLANTable(vlans)
                vlan_table.columns.hide("role")
                RequestConfig(request, paginate).configure(vlan_table)
                context["vlan_table"] = vlan_table
        return context


#
# Secrets
#


class SecretListView(generic.ObjectListView):
    queryset = Secret.objects.all()
    filterset = filters.SecretFilterSet
    filterset_form = forms.SecretFilterForm
    table = tables.SecretTable


class SecretView(generic.ObjectView):
    queryset = Secret.objects.all()

    def get_extra_context(self, request, instance):
        # Determine user's preferred output format
        if request.GET.get("format") in ["json", "yaml"]:
            format_ = request.GET.get("format")
            if request.user.is_authenticated:
                request.user.set_config("extras.configcontext.format", format_, commit=True)
        elif request.user.is_authenticated:
            format_ = request.user.get_config("extras.configcontext.format", "json")
        else:
            format_ = "json"

        provider = registry["secrets_providers"].get(instance.provider)

        groups = instance.secrets_groups.distinct()
        groups_table = tables.SecretsGroupTable(groups, orderable=False)

        return {
            "format": format_,
            "provider_name": provider.name if provider else instance.provider,
            "groups_table": groups_table,
        }


class SecretProviderParametersFormView(View):
    """
    Helper view to SecretView; retrieve the HTML form appropriate for entering parameters for a given SecretsProvider.
    """

    def get(self, request, provider_slug):
        provider = registry["secrets_providers"].get(provider_slug)
        if not provider:
            raise Http404
        return render(
            request,
            "extras/inc/secret_provider_parameters_form.html",
            {"form": provider.ParametersForm(initial=request.GET)},
        )


class SecretEditView(generic.ObjectEditView):
    queryset = Secret.objects.all()
    model_form = forms.SecretForm
    template_name = "extras/secret_edit.html"


class SecretDeleteView(generic.ObjectDeleteView):
    queryset = Secret.objects.all()


class SecretBulkImportView(generic.BulkImportView):  # 3.0 TODO: remove, unused
    queryset = Secret.objects.all()
    table = tables.SecretTable


class SecretBulkDeleteView(generic.BulkDeleteView):
    queryset = Secret.objects.all()
    filterset = filters.SecretFilterSet
    table = tables.SecretTable


class SecretsGroupListView(generic.ObjectListView):
    queryset = SecretsGroup.objects.all()
    filterset = filters.SecretsGroupFilterSet
    filterset_form = forms.SecretsGroupFilterForm
    table = tables.SecretsGroupTable
    action_buttons = ("add",)


class SecretsGroupView(generic.ObjectView):
    queryset = SecretsGroup.objects.all()

    def get_extra_context(self, request, instance):
        return {"secrets_group_associations": SecretsGroupAssociation.objects.filter(secrets_group=instance)}


class SecretsGroupEditView(generic.ObjectEditView):
    queryset = SecretsGroup.objects.all()
    model_form = forms.SecretsGroupForm
    template_name = "extras/secretsgroup_edit.html"

    def get_extra_context(self, request, instance):
        ctx = super().get_extra_context(request, instance)

        if request.POST:
            ctx["secrets"] = forms.SecretsGroupAssociationFormSet(data=request.POST, instance=instance)
        else:
            ctx["secrets"] = forms.SecretsGroupAssociationFormSet(instance=instance)

        return ctx

    def post(self, request, *args, **kwargs):
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

                    # Process the formsets for secrets
                    ctx = self.get_extra_context(request, obj)
                    secrets = ctx["secrets"]
                    if secrets.is_valid():
                        secrets.save()
                    else:
                        raise RuntimeError(secrets.errors)
                verb = "Created" if object_created else "Modified"
                msg = f"{verb} {self.queryset.model._meta.verbose_name}"
                logger.info(f"{msg} {obj} (PK: {obj.pk})")
                try:
                    msg = format_html('{} <a href="{}">{}</a>', msg, obj.get_absolute_url(), obj)
                except AttributeError:
                    msg = format_html("{} {}", msg, obj)
                messages.success(request, msg)

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
                msg = "Object save failed due to object-level permissions violation."
                logger.debug(msg)
                form.add_error(None, msg)
            except RuntimeError:
                msg = "Errors encountered when saving secrets group associations. See below."
                logger.debug(msg)
                form.add_error(None, msg)
            except ProtectedError as err:
                # e.g. Trying to delete a choice that is in use.
                err_msg = err.args[0]
                protected_obj = err.protected_objects[0]
                msg = f"{protected_obj.value}: {err_msg} Please cancel this edit and start again."
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


class SecretsGroupDeleteView(generic.ObjectDeleteView):
    queryset = SecretsGroup.objects.all()


class SecretsGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = SecretsGroup.objects.all()
    filterset = filters.SecretsGroupFilterSet
    table = tables.SecretsGroupTable


#
# Custom statuses
#


class StatusListView(generic.ObjectListView):
    """List `Status` objects."""

    queryset = Status.objects.all()
    filterset = filters.StatusFilterSet
    filterset_form = forms.StatusFilterForm
    table = tables.StatusTable


class StatusEditView(generic.ObjectEditView):
    """Edit a single `Status` object."""

    queryset = Status.objects.all()
    model_form = forms.StatusForm


class StatusBulkEditView(generic.BulkEditView):
    """Edit multiple `Status` objects."""

    queryset = Status.objects.all()
    table = tables.StatusTable
    form = forms.StatusBulkEditForm


class StatusBulkDeleteView(generic.BulkDeleteView):
    """Delete multiple `Status` objects."""

    queryset = Status.objects.all()
    table = tables.StatusTable


class StatusDeleteView(generic.ObjectDeleteView):
    """Delete a single `Status` object."""

    queryset = Status.objects.all()


class StatusBulkImportView(generic.BulkImportView):  # 3.0 TODO: remove, unused
    """Bulk CSV import of multiple `Status` objects."""

    queryset = Status.objects.all()
    table = tables.StatusTable


class StatusView(generic.ObjectView):
    """Detail view for a single `Status` object."""

    queryset = Status.objects.all()

    def get_extra_context(self, request, instance):
        """Return ordered content types."""
        return {"content_types": instance.content_types.order_by("app_label", "model")}


#
# Tags
#


class TagListView(generic.ObjectListView):
    queryset = Tag.objects.annotate(items=count_related(TaggedItem, "tag"))
    filterset = filters.TagFilterSet
    filterset_form = forms.TagFilterForm
    table = tables.TagTable


class TagView(generic.ObjectView):
    queryset = Tag.objects.all()

    def get_extra_context(self, request, instance):
        tagged_items = (
            TaggedItem.objects.filter(tag=instance).select_related("content_type").prefetch_related("content_object")
        )

        # Generate a table of all items tagged with this Tag
        items_table = tables.TaggedItemTable(tagged_items)
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(items_table)

        return {
            "items_count": tagged_items.count(),
            "items_table": items_table,
            "content_types": instance.content_types.order_by("app_label", "model"),
        }


class TagEditView(generic.ObjectEditView):
    queryset = Tag.objects.all()
    model_form = forms.TagForm
    template_name = "extras/tag_edit.html"


class TagDeleteView(generic.ObjectDeleteView):
    queryset = Tag.objects.all()


class TagBulkImportView(generic.BulkImportView):  # 3.0 TODO: remove, unused
    queryset = Tag.objects.all()
    table = tables.TagTable


class TagBulkEditView(generic.BulkEditView):
    queryset = Tag.objects.annotate(items=count_related(TaggedItem, "tag"))
    table = tables.TagTable
    form = forms.TagBulkEditForm
    filterset = filters.TagFilterSet


class TagBulkDeleteView(generic.BulkDeleteView):
    queryset = Tag.objects.annotate(items=count_related(TaggedItem, "tag"))
    table = tables.TagTable
    filterset = filters.TagFilterSet


#
# Teams
#


class TeamUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.TeamBulkEditForm
    filterset_class = filters.TeamFilterSet
    filterset_form_class = forms.TeamFilterForm
    form_class = forms.TeamForm
    queryset = Team.objects.all()
    serializer_class = serializers.TeamSerializer
    table_class = tables.TeamTable
    is_contact_associatable_model = False

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            contacts = instance.contacts.restrict(request.user, "view")
            contacts_table = tables.ContactTable(contacts, orderable=False)
            contacts_table.columns.hide("actions")
            paginate = {"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
            RequestConfig(request, paginate).configure(contacts_table)
            context["contacts_table"] = contacts_table

            # TODO: need some consistent ordering of contact_associations
            associations = instance.contact_associations.restrict(request.user, "view")
            associations_table = tables.ContactAssociationTable(associations, orderable=False)
            RequestConfig(request, paginate).configure(associations_table)
            context["contact_associations_table"] = associations_table
        return context


#
# Webhooks
#


class WebhookListView(generic.ObjectListView):
    queryset = Webhook.objects.all()
    table = tables.WebhookTable
    filterset = filters.WebhookFilterSet
    filterset_form = forms.WebhookFilterForm
    action_buttons = ("add",)


class WebhookView(generic.ObjectView):
    queryset = Webhook.objects.all()

    def get_extra_context(self, request, instance):
        return {"content_types": instance.content_types.order_by("app_label", "model")}


class WebhookEditView(generic.ObjectEditView):
    queryset = Webhook.objects.all()
    model_form = forms.WebhookForm


class WebhookDeleteView(generic.ObjectDeleteView):
    queryset = Webhook.objects.all()


class WebhookBulkDeleteView(generic.BulkDeleteView):
    queryset = Webhook.objects.all()
    table = tables.WebhookTable


#
# Job Extra Views
#
# NOTE: Due to inheritance, JobObjectChangeLogView and JobObjectNotesView can only be
# constructed below # ObjectChangeLogView and ObjectNotesView.


class JobObjectChangeLogView(ObjectChangeLogView):
    base_template = "extras/job_detail.html"


class JobObjectNotesView(ObjectNotesView):
    base_template = "extras/job_detail.html"
