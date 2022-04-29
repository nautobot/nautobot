import inspect
from datetime import datetime
import logging

from django import template
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.forms.utils import pretty_name
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.http import is_safe_url
from django.utils.safestring import mark_safe
from django.views.generic import View
from django_tables2 import RequestConfig
from jsonschema.validators import Draft7Validator

from nautobot.core.views import generic
from nautobot.dcim.models import Device
from nautobot.dcim.tables import DeviceTable
from nautobot.extras.utils import get_job_content_type, get_worker_count
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.forms import restrict_form_fields
from nautobot.utilities.utils import (
    copy_safe_request,
    count_related,
    get_table_for_model,
    prepare_cloned_fields,
    shallow_compare_dict,
)
from nautobot.utilities.tables import ButtonsColumn
from nautobot.utilities.views import ObjectPermissionRequiredMixin
from nautobot.utilities.utils import normalize_querydict
from nautobot.virtualization.models import VirtualMachine
from nautobot.virtualization.tables import VirtualMachineTable
from . import filters, forms, tables
from .choices import JobExecutionType, JobResultStatusChoices
from .datasources import (
    enqueue_git_repository_diff_origin_and_local,
    enqueue_pull_git_repository_and_refresh_data,
    get_datasource_contents,
)
from .jobs import get_job, run_job, Job as JobClass
from .models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomLink,
    DynamicGroup,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job as JobModel,
    ObjectChange,
    JobResult,
    Relationship,
    RelationshipAssociation,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    Tag,
    TaggedItem,
    Webhook,
)
from .registry import registry


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


class ComputedFieldDeleteView(generic.ObjectDeleteView):
    queryset = ComputedField.objects.all()


class ComputedFieldBulkDeleteView(generic.BulkDeleteView):
    queryset = ComputedField.objects.all()
    table = tables.ComputedFieldTable


#
# Config contexts
#

# TODO: disallow (or at least warn) user from manually editing config contexts that
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
            format = request.GET.get("format")
            if request.user.is_authenticated:
                request.user.set_config("extras.configcontext.format", format, commit=True)
        elif request.user.is_authenticated:
            format = request.user.get_config("extras.configcontext.format", "json")
        else:
            format = "json"

        return {
            "format": format,
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


class ObjectConfigContextView(generic.ObjectView):
    base_template = None
    template_name = "extras/object_configcontext.html"

    def get_extra_context(self, request, instance):
        source_contexts = ConfigContext.objects.restrict(request.user, "view").get_for_object(instance)

        # Determine user's preferred output format
        if request.GET.get("format") in ["json", "yaml"]:
            format = request.GET.get("format")
            if request.user.is_authenticated:
                request.user.set_config("extras.configcontext.format", format, commit=True)
        elif request.user.is_authenticated:
            format = request.user.get_config("extras.configcontext.format", "json")
        else:
            format = "json"

        return {
            "rendered_context": instance.get_config_context(),
            "source_contexts": source_contexts,
            "format": format,
            "base_template": self.base_template,
            "active_tab": "config-context",
        }


#
# Config context schemas
#

# TODO: disallow (or at least warn) user from manually editing config context schemas that
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
            format = request.GET.get("format")
            if request.user.is_authenticated:
                request.user.set_config("extras.configcontextschema.format", format, commit=True)
        elif request.user.is_authenticated:
            format = request.user.get_config("extras.configcontextschema.format", "json")
        else:
            format = "json"

        return {
            "format": format,
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
            data=instance.configcontext_set.all(),
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
            data=instance.device_set.prefetch_related(
                "tenant", "site", "rack", "device_type", "device_role", "primary_ip"
            ),
            orderable=False,
            extra_columns=[
                (
                    "validation_state",
                    tables.ConfigContextSchemaValidationStateColumn(validator, "local_context_data", empty_values=()),
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
            data=instance.virtualmachine_set.prefetch_related("cluster", "role", "tenant", "primary_ip"),
            orderable=False,
            extra_columns=[
                (
                    "validation_state",
                    tables.ConfigContextSchemaValidationStateColumn(validator, "local_context_data", empty_values=()),
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

    def get_changelog_url(self, instance):
        """Return the changelog URL."""
        route = "extras:customfield_changelog"
        return reverse(route, kwargs={"name": getattr(instance, "name")})


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

                    # Process the formsets for choices
                    ctx = self.get_extra_context(request, obj)
                    choices = ctx["choices"]
                    if choices.is_valid():
                        choices.save()
                    else:
                        raise RuntimeError(choices.errors)

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
            except RuntimeError:
                msg = "Errors encountered when saving custom field choices. See below."
                logger.debug(msg)
                form.add_error(None, msg)
            except ProtectedError as err:
                # e.g. Trying to delete a choice that is in use.
                protected_obj, err_msg = err.args
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


class CustomFieldDeleteView(generic.ObjectDeleteView):
    queryset = CustomField.objects.all()


class CustomFieldBulkDeleteView(generic.BulkDeleteView):
    queryset = CustomField.objects.all()
    table = tables.CustomFieldTable


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
            members = instance.get_queryset()
            members_table = table_class(members, orderable=False)

            # Paginate the members table.
            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(members_table)

            context["members_table"] = members_table

        return context


class DynamicGroupEditView(generic.ObjectEditView):
    queryset = DynamicGroup.objects.all()
    model_form = forms.DynamicGroupForm
    template_name = "extras/dynamicgroup_edit.html"

    def get_extra_context(self, request, instance):
        ctx = super().get_extra_context(request, instance)

        filterform_class = instance.generate_filter_form()

        if filterform_class is None:
            # FIXME(jathan): There is currently an edge case here that needs to be addressed:
            # `AttributeError: 'NoneType' object has no attribute 'is_valid'`
            # See: https://sentry.io/share/issue/fb41c6afb40248f6931021574bc38a0d/
            filter_form = None
        elif request.POST:
            filter_form = filterform_class(data=request.POST)
        else:
            initial = instance.get_initial()
            filter_form = filterform_class(initial=initial)

        ctx["filter_form"] = filter_form

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
                msg = "Object save failed due to object-level permissions violation."
                logger.debug(msg)
                form.add_error(None, msg)
            except RuntimeError:
                msg = "Errors encountered when saving Dynamic Group associations. See below."
                logger.debug(msg)
                form.add_error(None, msg)
            except ProtectedError as err:
                # e.g. Trying to delete a something that is in use.
                protected_obj, err_msg = err.args
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


class DynamicGroupDeleteView(generic.ObjectDeleteView):
    queryset = DynamicGroup.objects.all()


class DynamicGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = DynamicGroup.objects.all()
    table = tables.DynamicGroupTable


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
# Git repositories
#


class GitRepositoryListView(generic.ObjectListView):
    queryset = GitRepository.objects.all()
    # filterset = filters.GitRepositoryFilterSet
    # filterset_form = forms.GitRepositoryFilterForm
    table = tables.GitRepositoryTable
    template_name = "extras/gitrepository_list.html"

    def extra_context(self):
        git_repository_content_type = ContentType.objects.get(app_label="extras", model="gitrepository")
        # Get the newest results for each repository name
        results = {
            r.name: r
            for r in JobResult.objects.filter(
                obj_type=git_repository_content_type,
                status__in=JobResultStatusChoices.TERMINAL_STATE_CHOICES,
            )
            .order_by("completed")
            .defer("data")
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

    def alter_obj(self, obj, request, url_args, url_kwargs):
        # A GitRepository needs to know the originating request when it's saved so that it can enqueue using it
        obj.request = request
        return super().alter_obj(obj, request, url_args, url_kwargs)

    def get_return_url(self, request, obj):
        if request.method == "POST":
            return reverse("extras:gitrepository_result", kwargs={"slug": obj.slug})
        return super().get_return_url(request, obj)


class GitRepositoryDeleteView(generic.ObjectDeleteView):
    queryset = GitRepository.objects.all()


class GitRepositoryBulkImportView(generic.BulkImportView):
    queryset = GitRepository.objects.all()
    model_form = forms.GitRepositoryCSVForm
    table = tables.GitRepositoryBulkTable

    def _save_obj(self, obj_form, request):
        """Each GitRepository needs to know the originating request when it's saved so that it can enqueue using it."""
        instance = obj_form.save(commit=False)
        instance.request = request
        instance.save()

        return instance


class GitRepositoryBulkEditView(generic.BulkEditView):
    queryset = GitRepository.objects.prefetch_related("secrets_group")
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

    def extra_context(self):
        return {
            "datasource_contents": get_datasource_contents("extras.gitrepository"),
        }


def check_and_call_git_repository_function(request, slug, func):
    """Helper for checking Git permissions and worker availability, then calling provided function if all is well
    Args:
        request: request object.
        slug (str): GitRepository slug value.
        func (function): Enqueue git repo function.
    Returns:
        HttpResponseForbidden or a redirect
    """
    if not request.user.has_perm("extras.change_gitrepository"):
        return HttpResponseForbidden()

    # Allow execution only if a worker process is running.
    if not get_worker_count(request):
        messages.error(request, "Unable to run job: Celery worker process not running.")
    else:
        repository = get_object_or_404(GitRepository, slug=slug)
        func(repository, request)

    return redirect("extras:gitrepository_result", slug=slug)


class GitRepositorySyncView(View):
    def post(self, request, slug):
        return check_and_call_git_repository_function(request, slug, enqueue_pull_git_repository_and_refresh_data)


class GitRepositoryDryRunView(View):
    def post(self, request, slug):
        return check_and_call_git_repository_function(request, slug, enqueue_git_repository_diff_origin_and_local)


class GitRepositoryResultView(generic.ObjectView):
    """
    Display a JobResult and its Job data.
    """

    queryset = GitRepository.objects.all()
    template_name = "extras/gitrepository_result.html"

    def get_required_permission(self):
        return "extras.view_gitrepository"

    def get_extra_context(self, request, instance):
        git_repository_content_type = ContentType.objects.get(app_label="extras", model="gitrepository")
        job_result = (
            JobResult.objects.filter(obj_type=git_repository_content_type, name=instance.name)
            .order_by("-created")
            .first()
        )

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
    queryset = ImageAttachment.objects.all()
    model_form = forms.ImageAttachmentForm

    def alter_obj(self, imageattachment, request, args, kwargs):
        if not imageattachment.present_in_database:
            # Assign the parent object based on URL kwargs
            model = kwargs.get("model")
            imageattachment.parent = get_object_or_404(model, pk=kwargs["object_id"])
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
    template_name = "extras/job_list.html"

    def alter_queryset(self, request):
        queryset = super().alter_queryset(request)
        # Default to hiding "hidden" and non-installed jobs
        if "hidden" not in request.GET:
            queryset = queryset.filter(hidden=False)
        if "installed" not in request.GET:
            queryset = queryset.filter(installed=True)
        queryset = queryset.prefetch_related("results")
        return queryset

    def extra_context(self):
        return {
            "table_inc_template": "extras/inc/job_table.html",
        }


# 2.0 TODO: this should really be "JobRunView"
class JobView(ObjectPermissionRequiredMixin, View):
    """
    View the parameters of a Job and enqueue it if desired.
    """

    queryset = JobModel.objects.all()

    def get_required_permission(self):
        return "extras.run_job"

    def _get_job_model_or_404(self, class_path=None, slug=None):
        """Helper function for get() and post()."""
        if class_path:
            try:
                job_model = self.queryset.get_for_class_path(class_path)
            except JobModel.DoesNotExist:
                raise Http404
        else:
            job_model = get_object_or_404(self.queryset, slug=slug)

        return job_model

    def get(self, request, class_path=None, slug=None):
        job_model = self._get_job_model_or_404(class_path, slug)

        try:
            job_form = job_model.job_class().as_form(initial=normalize_querydict(request.GET))
        except RuntimeError as err:
            messages.error(request, f"Unable to run or schedule '{job_model}': {err}")
            return redirect("extras:job_list")

        schedule_form = forms.JobScheduleForm(initial=normalize_querydict(request.GET))

        return render(
            request,
            "extras/job.html",  # 2.0 TODO: extras/job_submission.html
            {
                "job_model": job_model,
                "job_form": job_form,
                "schedule_form": schedule_form,
            },
        )

    def post(self, request, class_path=None, slug=None):
        job_model = self._get_job_model_or_404(class_path, slug)

        job_form = (
            job_model.job_class().as_form(request.POST, request.FILES) if job_model.job_class is not None else None
        )
        schedule_form = forms.JobScheduleForm(request.POST)

        # Allow execution only if a worker process is running and the job is runnable.
        if not get_worker_count(request):
            messages.error(request, "Unable to run or schedule job: Celery worker process not running.")
        elif not job_model.installed or job_model.job_class is None:
            messages.error(request, "Unable to run or schedule job: Job is not presently installed.")
        elif not job_model.enabled:
            messages.error(request, "Unable to run or schedule job: Job is not enabled to be run.")
        elif job_form is not None and job_form.is_valid() and schedule_form.is_valid():
            # Run the job. A new JobResult is created.
            commit = job_form.cleaned_data.pop("_commit")
            schedule_type = schedule_form.cleaned_data["_schedule_type"]

            if job_model.approval_required or schedule_type in JobExecutionType.SCHEDULE_CHOICES:

                if schedule_type in JobExecutionType.SCHEDULE_CHOICES:
                    # Schedule the job instead of running it now
                    schedule_name = schedule_form.cleaned_data["_schedule_name"]
                    schedule_datetime = schedule_form.cleaned_data["_schedule_start_time"]

                else:
                    # The job must be approved.
                    # If the schedule_type is immediate, we still create the task, but mark it for approval
                    # as a once in the future task with the due date set to the current time. This means
                    # when approval is granted, the task is immediately due for execution.
                    schedule_type = JobExecutionType.TYPE_FUTURE
                    schedule_datetime = datetime.now()
                    schedule_name = f"{job_model} - {schedule_datetime}"

                job_kwargs = {
                    "data": job_model.job_class.serialize_data(job_form.cleaned_data),
                    "request": copy_safe_request(request),
                    "user": request.user.pk,
                    "commit": commit,
                    "name": job_model.class_path,
                }

                scheduled_job = ScheduledJob(
                    name=schedule_name,
                    task="nautobot.extras.jobs.scheduled_job_handler",
                    job_class=job_model.class_path,
                    job_model=job_model,
                    start_time=schedule_datetime,
                    description=f"Nautobot job {schedule_name} scheduled by {request.user} for {schedule_datetime}",
                    kwargs=job_kwargs,
                    interval=schedule_type,
                    one_off=schedule_type == JobExecutionType.TYPE_FUTURE,
                    user=request.user,
                    approval_required=job_model.approval_required,
                )
                scheduled_job.kwargs["scheduled_job_pk"] = scheduled_job.pk
                scheduled_job.save()

                if job_model.approval_required:
                    messages.success(request, f"Job {schedule_name} successfully submitted for approval")
                    return redirect("extras:scheduledjob_approval_queue_list")
                else:
                    messages.success(request, f"Job {schedule_name} successfully scheduled")
                    return redirect("extras:scheduledjob_list")

            else:
                # Enqueue job for immediate execution
                job_content_type = get_job_content_type()
                job_result = JobResult.enqueue_job(
                    run_job,
                    job_model.class_path,
                    job_content_type,
                    request.user,
                    data=job_model.job_class.serialize_data(job_form.cleaned_data),
                    request=copy_safe_request(request),
                    commit=commit,
                )

                return redirect("extras:job_jobresult", pk=job_result.pk)

        return render(
            request,
            "extras/job.html",
            {
                "job_model": job_model,
                "job_form": job_form,
                "schedule_form": schedule_form,
            },
        )


# 2.0 TODO: this should really be "JobView"
class JobDetailView(generic.ObjectView):
    queryset = JobModel.objects.all()
    template_name = "extras/job_detail.html"


class JobEditView(generic.ObjectEditView):
    queryset = JobModel.objects.all()
    model_form = forms.JobEditForm
    template_name = "extras/job_edit.html"


class JobDeleteView(generic.ObjectDeleteView):
    queryset = JobModel.objects.all()


class JobApprovalRequestView(generic.ObjectView):
    """
    This view handles requests to view and approve a Job execution request.
    It renders the Job's form in much the same way as `JobView` except all
    form fields are disabled and actions on the form relate to approval of the
    job's execution, rather than initial job form input.
    """

    queryset = ScheduledJob.objects.filter(task="nautobot.extras.jobs.scheduled_job_handler").needs_approved()
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
            initial = instance.kwargs.get("data", {})
            initial["_commit"] = instance.kwargs.get("commit", True)
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
            else:
                # Immediately enqueue the job with commit=False and send the user to the normal JobResult view
                job_content_type = get_job_content_type()
                initial = scheduled_job.kwargs.get("data", {})
                initial["_commit"] = False
                job_result = JobResult.enqueue_job(
                    run_job,
                    job_model.job_class.class_path,
                    job_content_type,
                    request.user,
                    data=job_model.job_class.serialize_data(initial),
                    request=copy_safe_request(request),
                    commit=False,  # force a dry-run
                )

                return redirect("extras:job_jobresult", pk=job_result.pk)
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
    queryset = ScheduledJob.objects.filter(task="nautobot.extras.jobs.scheduled_job_handler").enabled()
    table = tables.ScheduledJobTable
    filterset = filters.ScheduledJobFilterSet
    filterset_form = forms.ScheduledJobFilterForm
    action_buttons = ("delete",)


class ScheduledJobBulkDeleteView(generic.BulkDeleteView):
    queryset = ScheduledJob.objects.all()
    table = tables.ScheduledJobTable
    filterset = filters.ScheduledJobFilterSet


class ScheduledJobApprovalQueueListView(generic.ObjectListView):
    queryset = ScheduledJob.objects.filter(task="nautobot.extras.jobs.scheduled_job_handler").needs_approved()
    table = tables.ScheduledJobApprovalQueueTable
    filterset = filters.ScheduledJobFilterSet
    filterset_form = forms.ScheduledJobFilterForm
    action_buttons = ()
    template_name = "extras/scheduled_jobs_approval_queue_list.html"


class ScheduledJobView(generic.ObjectView):
    queryset = ScheduledJob.objects.all()

    def _get_job(self, class_path):
        job_class = get_job(class_path)
        if job_class is None:
            raise Http404
        return job_class

    def get_extra_context(self, request, instance):
        job_class = self._get_job(instance.job_class)
        labels = {}
        for name, var in job_class._get_vars().items():
            field = var.as_field()
            if field.label:
                labels[name] = var
            else:
                labels[name] = pretty_name(name)
        return {"labels": labels}


class ScheduledJobDeleteView(generic.ObjectDeleteView):
    queryset = ScheduledJob.objects.all()


#
# JobResult
#


class JobResultListView(generic.ObjectListView):
    """
    List JobResults
    """

    queryset = JobResult.objects.prefetch_related("job_model", "logs", "obj_type", "user")
    filterset = filters.JobResultFilterSet
    filterset_form = forms.JobResultFilterForm
    table = tables.JobResultTable
    action_buttons = ()


class JobResultDeleteView(generic.ObjectDeleteView):
    queryset = JobResult.objects.all()


class JobResultBulkDeleteView(generic.BulkDeleteView):
    queryset = JobResult.objects.all()
    table = tables.JobResultTable


class JobResultView(generic.ObjectView):
    """
    Display a JobResult and its Job data.
    """

    queryset = JobResult.objects.all()
    template_name = "extras/jobresult.html"

    def get_extra_context(self, request, instance):
        associated_record = None
        job_class = None
        if instance.job_model is not None:
            job_class = instance.job_model.job_class
        # 2.0 TODO: remove JobResult.related_object entirely
        related_object = instance.related_object
        if inspect.isclass(related_object) and issubclass(related_object, JobClass):
            if job_class is None:
                job_class = related_object
        elif related_object:
            associated_record = related_object

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
        log_table = tables.JobLogEntryTable(data=instance.logs.all(), user=request.user)
        RequestConfig(request).configure(log_table)
        return HttpResponse(log_table.as_html(request))


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

    # TODO: Remove this remapping in 2.0 as it is addressing a potentially breaking change
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
        related_changes = (
            ObjectChange.objects.restrict(request.user, "view")
            .filter(request_id=instance.request_id)
            .exclude(pk=instance.pk)
        )
        related_changes_table = tables.ObjectChangeTable(data=related_changes[:50], orderable=False)

        objectchanges = ObjectChange.objects.restrict(request.user, "view").filter(
            changed_object_type=instance.changed_object_type,
            changed_object_id=instance.changed_object_id,
        )

        next_change = objectchanges.filter(time__gt=instance.time).order_by("time").first()
        prev_change = objectchanges.filter(time__lt=instance.time).order_by("-time").first()

        if prev_change:
            diff_added = shallow_compare_dict(
                prev_change.object_data,
                instance.object_data,
                exclude=["last_updated"],
            )
            diff_removed = {x: prev_change.object_data.get(x) for x in diff_added}
        else:
            # No previous change; this is the initial change that added the object
            diff_added = diff_removed = instance.object_data

        return {
            "diff_added": diff_added,
            "diff_removed": diff_removed,
            "next_change": next_change,
            "prev_change": prev_change,
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
            .prefetch_related("user", "changed_object_type")
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

        # Default to using "<app>/<model>.html" as the template, if it exists. Otherwise,
        # fall back to using base.html.
        if self.base_template is None:
            self.base_template = f"{model._meta.app_label}/{model._meta.model_name}.html"
            # TODO: This can be removed once an object view has been established for every model.
            try:
                template.loader.get_template(self.base_template)
            except template.TemplateDoesNotExist:
                self.base_template = "base.html"

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


class RelationshipEditView(generic.ObjectEditView):
    queryset = Relationship.objects.all()
    model_form = forms.RelationshipForm


class RelationshipBulkDeleteView(generic.BulkDeleteView):
    queryset = Relationship.objects.all()
    table = tables.RelationshipTable


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


class RelationshipAssociationDeleteView(generic.ObjectDeleteView):
    queryset = RelationshipAssociation.objects.all()


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
            format = request.GET.get("format")
            if request.user.is_authenticated:
                request.user.set_config("extras.configcontext.format", format, commit=True)
        elif request.user.is_authenticated:
            format = request.user.get_config("extras.configcontext.format", "json")
        else:
            format = "json"

        provider = registry["secrets_providers"].get(instance.provider)

        groups = instance.groups.distinct()
        groups_table = tables.SecretsGroupTable(groups, orderable=False)

        return {
            "format": format,
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


class SecretBulkImportView(generic.BulkImportView):
    queryset = Secret.objects.all()
    model_form = forms.SecretCSVForm
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
    action_buttons = (
        "add",
        "delete",
    )


class SecretsGroupView(generic.ObjectView):
    queryset = SecretsGroup.objects.all()

    def get_extra_context(self, request, instance):
        return {"secrets_group_associations": SecretsGroupAssociation.objects.filter(group=instance)}


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
                msg = "Object save failed due to object-level permissions violation."
                logger.debug(msg)
                form.add_error(None, msg)
            except RuntimeError:
                msg = "Errors encountered when saving secrets group associations. See below."
                logger.debug(msg)
                form.add_error(None, msg)
            except ProtectedError as err:
                # e.g. Trying to delete a choice that is in use.
                protected_obj, err_msg = err.args
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


class StatusBulkImportView(generic.BulkImportView):
    """Bulk CSV import of multiple `Status` objects."""

    queryset = Status.objects.all()
    model_form = forms.StatusCSVForm
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
        tagged_items = TaggedItem.objects.filter(tag=instance).prefetch_related("content_type", "content_object")

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


class TagBulkImportView(generic.BulkImportView):
    queryset = Tag.objects.all()
    model_form = forms.TagCSVForm
    table = tables.TagTable


class TagBulkEditView(generic.BulkEditView):
    queryset = Tag.objects.annotate(items=count_related(TaggedItem, "tag"))
    table = tables.TagTable
    form = forms.TagBulkEditForm


class TagBulkDeleteView(generic.BulkDeleteView):
    queryset = Tag.objects.annotate(items=count_related(TaggedItem, "tag"))
    table = tables.TagTable


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
