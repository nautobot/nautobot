from functools import partial
import logging
from typing import Optional
from urllib.parse import parse_qs

from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.forms.utils import pretty_name
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import urlencode
from django.template.loader import get_template, TemplateDoesNotExist
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.encoding import iri_to_uri
from django.utils.html import format_html, format_html_join
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import get_current_timezone
from django.views.generic import View
from django_tables2 import RequestConfig
from jsonschema.validators import Draft7Validator
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from nautobot.core.choices import ButtonActionColorChoices
from nautobot.core.constants import PAGINATE_COUNT_DEFAULT
from nautobot.core.exceptions import FilterSetFieldNotFound
from nautobot.core.forms import ApprovalForm, restrict_form_fields
from nautobot.core.models.querysets import count_related
from nautobot.core.models.utils import pretty_print_query
from nautobot.core.tables import ButtonsColumn
from nautobot.core.templatetags import helpers
from nautobot.core.ui import object_detail
from nautobot.core.ui.breadcrumbs import (
    BaseBreadcrumbItem,
    Breadcrumbs,
    context_object_attr,
    InstanceParentBreadcrumbItem,
    ModelBreadcrumbItem,
    ViewNameBreadcrumbItem,
)
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.ui.titles import Titles
from nautobot.core.utils.config import get_settings_or_config
from nautobot.core.utils.lookup import (
    get_filterset_for_model,
    get_model_for_view_name,
    get_route_for_model,
    get_table_class_string_from_view_name,
    get_table_for_model,
)
from nautobot.core.utils.requests import is_single_choice_field, normalize_querydict
from nautobot.core.views import generic, viewsets
from nautobot.core.views.mixins import (
    ObjectBulkCreateViewMixin,
    ObjectBulkDestroyViewMixin,
    ObjectBulkUpdateViewMixin,
    ObjectChangeLogViewMixin,
    ObjectDataComplianceViewMixin,
    ObjectDestroyViewMixin,
    ObjectDetailViewMixin,
    ObjectEditViewMixin,
    ObjectListViewMixin,
    ObjectNotesViewMixin,
    ObjectPermissionRequiredMixin,
)
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.utils import common_detail_view_context, get_obj_from_context, prepare_cloned_fields
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.dcim.models import Controller, Device, Interface, Module, Rack, VirtualDeviceContext
from nautobot.dcim.tables import (
    ControllerTable,
    DeviceTable,
    InterfaceTable,
    ModuleTable,
    RackTable,
    VirtualDeviceContextTable,
)
from nautobot.extras.context_managers import deferred_change_logging_for_bulk_operation
from nautobot.extras.templatetags.approvals import render_approval_workflow_state
from nautobot.extras.utils import (
    fixup_filterset_query_params,
    get_base_template,
    get_pending_approval_workflow_stages,
    get_worker_count,
)
from nautobot.ipam.models import IPAddress, Prefix, VLAN
from nautobot.ipam.tables import IPAddressTable, PrefixTable, VLANTable
from nautobot.virtualization.models import VirtualMachine, VMInterface
from nautobot.virtualization.tables import VirtualMachineTable, VMInterfaceTable
from nautobot.vpn.models import VPN, VPNProfile, VPNTunnel, VPNTunnelEndpoint
from nautobot.vpn.tables import VPNProfileTable, VPNTable, VPNTunnelEndpointTable, VPNTunnelTable

from . import filters, forms, jobs_ui, tables
from .api import serializers
from .choices import (
    ApprovalWorkflowStateChoices,
    DynamicGroupTypeChoices,
    JobExecutionType,
    JobQueueTypeChoices,
    JobResultStatusChoices,
)
from .datasources import (
    enqueue_git_repository_diff_origin_and_local,
    enqueue_pull_git_repository_and_refresh_data,
    get_datasource_contents,
)
from .jobs import get_job
from .models import (
    ApprovalWorkflow,
    ApprovalWorkflowDefinition,
    ApprovalWorkflowStage,
    ApprovalWorkflowStageDefinition,
    ApprovalWorkflowStageResponse,
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
    JobQueue,
    JobResult,
    MetadataType,
    Note,
    ObjectChange,
    ObjectMetadata,
    Relationship,
    RelationshipAssociation,
    Role,
    SavedView,
    ScheduledJob,
    Secret,
    SecretsGroup,
    StaticGroupAssociation,
    Status,
    Tag,
    TaggedItem,
    Team,
    UserSavedViewAssociation,
    Webhook,
)
from .registry import registry

logger = logging.getLogger(__name__)

#
# Approval Workflows
#


class ApprovalWorkflowDefinitionUIViewSet(NautobotUIViewSet):
    """ViewSet for ApprovalWorkflowDefinition."""

    bulk_update_form_class = forms.ApprovalWorkflowDefinitionBulkEditForm
    filterset_class = filters.ApprovalWorkflowDefinitionFilterSet
    filterset_form_class = forms.ApprovalWorkflowDefinitionFilterForm
    form_class = forms.ApprovalWorkflowDefinitionForm
    queryset = ApprovalWorkflowDefinition.objects.all()
    serializer_class = serializers.ApprovalWorkflowDefinitionSerializer
    table_class = tables.ApprovalWorkflowDefinitionTable

    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                table_class=tables.ApprovalWorkflowStageDefinitionTable,
                table_filter="approval_workflow_definition",
                section=SectionChoices.RIGHT_HALF,
                exclude_columns=["approval_workflow_definition", "actions"],
                add_button_route=None,
                table_title="Stages",
            ),
            object_detail.ObjectsTablePanel(
                weight=200,
                table_class=tables.ApprovalWorkflowTable,
                table_filter="approval_workflow_definition",
                section=SectionChoices.FULL_WIDTH,
                exclude_columns=["object_under_review_content_type", "approval_workflow_definition"],
                add_button_route=None,
                table_title="Workflows",
            ),
        ],
    )

    def get_extra_context(self, request, instance):
        ctx = super().get_extra_context(request, instance)
        if self.action in ("create", "update"):
            if request.POST:
                ctx["stages"] = forms.ApprovalWorkflowStageDefinitionFormSet(data=request.POST, instance=instance)
            else:
                ctx["stages"] = forms.ApprovalWorkflowStageDefinitionFormSet(instance=instance)

        return ctx

    def form_save(self, form, **kwargs):
        obj = super().form_save(form, **kwargs)

        # Process the formset for stages
        ctx = self.get_extra_context(self.request, obj)
        stages = ctx["stages"]
        if stages.is_valid():
            stages.save()
        else:
            raise ValidationError(stages.errors)

        return obj


class ApprovalWorkflowStageDefinitionUIViewSet(NautobotUIViewSet):
    """ViewSet for ApprovalWorkflowStageDefinition."""

    bulk_update_form_class = forms.ApprovalWorkflowStageDefinitionBulkEditForm
    filterset_class = filters.ApprovalWorkflowStageDefinitionFilterSet
    filterset_form_class = forms.ApprovalWorkflowStageDefinitionFilterForm
    form_class = forms.ApprovalWorkflowStageDefinitionForm
    queryset = ApprovalWorkflowStageDefinition.objects.all()
    serializer_class = serializers.ApprovalWorkflowStageDefinitionSerializer
    table_class = tables.ApprovalWorkflowStageDefinitionTable

    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
        ],
    )


class ApprovalWorkflowUIViewSet(
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectDestroyViewMixin,
    ObjectBulkDestroyViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
):
    """ViewSet for ApprovalWorkflow."""

    filterset_class = filters.ApprovalWorkflowFilterSet
    filterset_form_class = forms.ApprovalWorkflowFilterForm
    queryset = ApprovalWorkflow.objects.all()
    serializer_class = serializers.ApprovalWorkflowSerializer
    table_class = tables.ApprovalWorkflowTable
    action_buttons = ()

    class ApprovalWorkflowPanel(object_detail.ObjectFieldsPanel):
        def __init__(self, **kwargs):
            super().__init__(
                fields=(
                    "approval_workflow_definition",
                    "object_under_review",
                    "current_state",
                    "decision_date",
                    "user",
                ),
                value_transforms={
                    "current_state": [render_approval_workflow_state],
                },
                hide_if_unset=("decision_date"),
                **kwargs,
            )

        def render_key(self, key, value, context):
            obj = get_obj_from_context(context)

            if key == "object_under_review":
                return helpers.bettertitle(obj.object_under_review_content_type.model_class()._meta.verbose_name)
            if key == "user":
                return "Requesting User"
            if key == "decision_date":
                if obj.current_state == ApprovalWorkflowStateChoices.APPROVED:
                    return "Approval Date"
                elif obj.current_state == ApprovalWorkflowStateChoices.DENIED:
                    return "Denial Date"

            return super().render_key(key, value, context)

        def render_value(self, key, value, context):
            obj = get_obj_from_context(context)
            if key == "user":
                if not obj.user:
                    return obj.user_name

            return super().render_value(key, value, context)

    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            ApprovalWorkflowPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
            ),
            object_detail.ObjectsTablePanel(
                weight=200,
                table_title="Stages",
                table_class=tables.RelatedApprovalWorkflowStageTable,
                table_filter="approval_workflow",
                section=SectionChoices.RIGHT_HALF,
                exclude_columns=["approval_workflow"],
                add_button_route=None,
            ),
            object_detail.ObjectsTablePanel(
                weight=200,
                table_title="Responses",
                table_class=tables.RelatedApprovalWorkflowStageResponseTable,
                table_filter="approval_workflow_stage__approval_workflow",
                section=SectionChoices.FULL_WIDTH,
                exclude_columns=["approval_workflow"],
                add_button_route=None,
                enable_related_link=False,
            ),
        ],
    )


class ApprovalWorkflowStageUIViewSet(
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectDestroyViewMixin,
    ObjectBulkDestroyViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
):
    """ViewSet for ApprovalWorkflowStage."""

    filterset_class = filters.ApprovalWorkflowStageFilterSet
    filterset_form_class = forms.ApprovalWorkflowStageFilterForm
    queryset = ApprovalWorkflowStage.objects.all()
    serializer_class = serializers.ApprovalWorkflowStageSerializer
    table_class = tables.ApprovalWorkflowStageTable
    action_buttons = ()

    class ApprovalWorkflowStagePanel(object_detail.ObjectFieldsPanel):
        def __init__(self, **kwargs):
            super().__init__(
                fields=(
                    "approval_workflow",
                    "state",
                    "decision_date",
                    "approver_group",
                    "min_approvers",
                ),
                value_transforms={
                    "state": [render_approval_workflow_state],
                },
                hide_if_unset=("decision_date"),
                ignore_nonexistent_fields=True,
                **kwargs,
            )

        def render_key(self, key, value, context):
            obj = get_obj_from_context(context)

            if key == "approval_workflow":
                return "Approval Workflow"
            if key == "decision_date":
                if obj.state == ApprovalWorkflowStateChoices.APPROVED:
                    return "Approval Date"
                elif obj.state == ApprovalWorkflowStateChoices.DENIED:
                    return "Denial Date"
            if key == "min_approvers":
                return "Minimum Number of Approvers Needed"

            return super().render_key(key, value, context)

        def render_value(self, key, value, context):
            if key == "approver_group":
                user_html = format_html(
                    "<span>{}</span><ul>{}</ul>",
                    value,
                    format_html_join("\n", "<li>{}</li>", ((user,) for user in value.user_set.all())),
                )
                return user_html

            return super().render_value(key, value, context)

        def get_data(self, context):
            obj = get_obj_from_context(context)
            data = super().get_data(context)
            data["approver_group"] = obj.approval_workflow_stage_definition.approver_group
            data["min_approvers"] = obj.approval_workflow_stage_definition.min_approvers
            return data

    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            ApprovalWorkflowStagePanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
            ),
            object_detail.ObjectsTablePanel(
                weight=200,
                table_class=tables.ApprovalWorkflowStageResponseTable,
                table_filter="approval_workflow_stage",
                section=SectionChoices.FULL_WIDTH,
                exclude_columns=["approval_workflow_stage"],
                table_title="Responses",
                enable_related_link=False,
            ),
        ],
    )

    @action(
        detail=True,
        url_path="approve",
        methods=["get", "post"],
        custom_view_base_action="change",
        custom_view_additional_permissions=["extras.view_approvalworkflowstage"],
    )
    def approve(self, request, *args, **kwargs):
        """
        Approve the approval workflow stage response.
        """
        instance = self.get_object()

        if not (
            request.user.is_superuser
            or instance.approval_workflow_stage_definition.approver_group.user_set.filter(id=request.user.id).exists()
        ):
            messages.error(request, "You are not permitted to approve this workflow stage.")
            return redirect(self.get_return_url(request, instance))

        if request.method == "GET":
            if existing_response := ApprovalWorkflowStageResponse.objects.filter(
                approval_workflow_stage=instance, user=request.user
            ).first():
                form = ApprovalForm(initial={"comments": existing_response.comments})
            else:
                form = ApprovalForm()

            object_under_review = instance.approval_workflow.object_under_review
            template_name = getattr(object_under_review, "get_approval_template", lambda: None)()
            if not template_name:
                template_name = "extras/approval_workflow/approve.html"

            return render(
                request,
                template_name,
                {
                    "obj": instance,
                    "object_under_review": instance.approval_workflow.object_under_review,
                    "form": form,
                    "obj_type": ApprovalWorkflowStage._meta.verbose_name,
                    "return_url": self.get_return_url(request, instance),
                    "card_class": "success",
                    "button_class": "success",
                },
            )

        approval_workflow_stage_response, _ = ApprovalWorkflowStageResponse.objects.get_or_create(
            approval_workflow_stage=instance, user=request.user
        )
        approval_workflow_stage_response.comments = request.data.get("comments")
        approval_workflow_stage_response.state = ApprovalWorkflowStateChoices.APPROVED
        approval_workflow_stage_response.save()
        instance.refresh_from_db()
        messages.success(request, f"You approved {instance}.")
        return redirect(self.get_return_url(request))

    @action(
        detail=True,
        url_path="deny",
        methods=["get", "post"],
        custom_view_base_action="change",
        custom_view_additional_permissions=["extras.view_approvalworkflowstage"],
    )
    def deny(self, request, *args, **kwargs):
        """
        Deny the approval workflow stage response.
        """
        instance = self.get_object()

        if not (
            request.user.is_superuser
            or instance.approval_workflow_stage_definition.approver_group.user_set.filter(id=request.user.id).exists()
        ):
            messages.error(request, "You are not permitted to deny this workflow stage.")
            return redirect(self.get_return_url(request, instance))

        if request.method == "GET":
            if existing_response := ApprovalWorkflowStageResponse.objects.filter(
                approval_workflow_stage=instance, user=request.user
            ).first():
                form = ApprovalForm(initial={"comments": existing_response.comments})
            else:
                form = ApprovalForm()

            return render(
                request,
                "extras/approval_workflow/deny.html",
                {
                    "obj": instance,
                    "object_under_review": instance.approval_workflow.object_under_review,
                    "form": form,
                    "obj_type": ApprovalWorkflowStage._meta.verbose_name,
                    "return_url": self.get_return_url(request, instance),
                },
            )

        approval_workflow_stage_response, _ = ApprovalWorkflowStageResponse.objects.get_or_create(
            approval_workflow_stage=instance, user=request.user
        )
        approval_workflow_stage_response.comments = request.data.get("comments")
        approval_workflow_stage_response.state = ApprovalWorkflowStateChoices.DENIED
        approval_workflow_stage_response.save()
        instance.refresh_from_db()
        messages.success(request, f"You denied {instance}.")
        return redirect(self.get_return_url(request))

    @action(
        detail=True,
        url_path="comment",
        methods=["get", "post"],
        custom_view_base_action="change",
        custom_view_additional_permissions=["extras.view_approvalworkflowstage"],
    )
    def comment(self, request, *args, **kwargs):
        """
        Comment the approval workflow stage response.
        """
        instance = self.get_object()

        if not instance.is_not_done_stage:
            messages.error(
                request, f"This stage is in {instance.state} state. Can't comment on an approved or denied stage."
            )
            return redirect(self.get_return_url(request, instance))

        # We don't enforce approver-group/superuser check here, anyone can comment, not just an approver.

        if request.method == "GET":
            if existing_response := ApprovalWorkflowStageResponse.objects.filter(
                approval_workflow_stage=instance, user=request.user
            ).first():
                form = ApprovalForm(initial={"comments": existing_response.comments})
            else:
                form = ApprovalForm()

            template_name = "extras/approval_workflow/comment.html"

            return render(
                request,
                template_name,
                {
                    "obj": instance,
                    "object_under_review": instance.approval_workflow.object_under_review,
                    "form": form,
                    "obj_type": ApprovalWorkflowStage._meta.verbose_name,
                    "return_url": self.get_return_url(request, instance),
                },
            )

        approval_workflow_stage_response, _ = ApprovalWorkflowStageResponse.objects.get_or_create(
            approval_workflow_stage=instance, user=request.user
        )
        approval_workflow_stage_response.comments = request.data.get("comments")
        # we don't want to change a state if is approved, denied or canceled
        if approval_workflow_stage_response.state == ApprovalWorkflowStateChoices.PENDING:
            approval_workflow_stage_response.state = ApprovalWorkflowStateChoices.COMMENT
        approval_workflow_stage_response.save()
        instance.refresh_from_db()
        messages.success(request, f"You commented {instance}.")
        return redirect(self.get_return_url(request))


class ApprovalWorkflowStageResponseUIViewSet(
    ObjectBulkDestroyViewMixin,
    ObjectDestroyViewMixin,
):
    """ViewSet for ApprovalWorkflowStageResponse."""

    filterset_class = filters.ApprovalWorkflowStageResponseFilterSet
    filterset_form_class = forms.ApprovalWorkflowStageResponseFilterForm
    queryset = ApprovalWorkflowStageResponse.objects.all()
    serializer_class = serializers.ApprovalWorkflowStageResponseSerializer
    table_class = tables.ApprovalWorkflowStageResponseTable
    object_detail_content = None


class ApproverDashboardView(ObjectListViewMixin):
    """
    View for the dashboard of approval workflow stages waiting for the current user to approve.
    """

    queryset = ApprovalWorkflowStage.objects.all()
    filterset_class = filters.ApprovalWorkflowStageFilterSet
    filterset_form_class = forms.ApprovalWorkflowStageFilterForm
    table_class = tables.ApproverDashboardTable
    template_name = "extras/approval_dashboard.html"
    action_buttons = ()

    def get_template_name(self):
        """
        Override the template names to use the custom dashboard template.
        """
        return self.template_name

    def get_extra_context(self, request, instance):
        """
        Get the extra context for the dashboard view.
        """
        context = super().get_extra_context(request, instance)
        context["title"] = "My Approvals"
        context["approval_view"] = True
        return context

    def get_queryset(self):
        """
        Filter the queryset to only include approval workflow stages that are pending approval
        and are assigned to the current user for approval.
        """
        return get_pending_approval_workflow_stages(self.request.user, super().get_queryset())

    def list(self, request, *args, **kwargs):
        """
        Override the list method to display a helpful message regarding the page.
        """
        messages.info(
            request,
            "You are viewing a dashboard of approval workflow stages that are pending for your approval.",
        )
        return super().list(request, *args, **kwargs)


class ApproveeDashboardView(ObjectListViewMixin):
    """
    View for the dashboard of approval workflows trigger by the current user.
    """

    queryset = ApprovalWorkflow.objects.all()
    filterset_class = filters.ApprovalWorkflowFilterSet
    filterset_form_class = forms.ApprovalWorkflowFilterForm
    table_class = tables.ApprovalWorkflowTable
    template_name = "extras/approval_dashboard.html"
    action_buttons = ()

    def get_template_name(self):
        """
        Override the template names to use the custom dashboard template.
        """
        return self.template_name

    def get_extra_context(self, request, instance):
        """
        Get the extra context for the dashboard view.
        """
        context = super().get_extra_context(request, instance)
        context["title"] = "My Requests"
        return context

    def get_queryset(self):
        """
        Filter the queryset to only include workflows that triggered by the current users.
        """
        user = self.request.user
        if user.is_anonymous:
            return ApprovalWorkflow.objects.none()
        queryset = super().get_queryset()
        return queryset.filter(user=user).order_by("created")

    def list(self, request, *args, **kwargs):
        """
        Override the list method to display a helpful message regarding the page.
        """
        messages.info(
            request,
            "You are viewing a dashboard of approval workflows that are requested by you.",
        )
        return super().list(request, *args, **kwargs)


class ObjectApprovalWorkflowView(generic.GenericView):
    """
    Present an pending approval workflow attached to a particular object.

    base_template: Specify to explicitly identify the base object detail template to render.
        If not provided, "<app>/<model>.html", "<app>/<model>_retrieve.html", or "generic/object_retrieve.html"
        will be used, as per `get_base_template()`.
    """

    base_template: Optional[str] = None

    def get(self, request, model, **kwargs):
        # Handle QuerySet restriction of parent object if needed

        if hasattr(model.objects, "restrict"):
            obj = get_object_or_404(model.objects.restrict(request.user, "view"), **kwargs)
        else:
            obj = get_object_or_404(model, **kwargs)

        # Gather all changes for this object (and its related objects)
        approval_workflow = ApprovalWorkflow.objects.get(object_under_review_object_id=obj.pk)
        stage_table = tables.RelatedApprovalWorkflowStageTable(
            ApprovalWorkflowStage.objects.filter(approval_workflow=approval_workflow),
        )
        stage_table.columns.hide("approval_workflow")
        response_table = tables.RelatedApprovalWorkflowStageResponseTable(
            ApprovalWorkflowStageResponse.objects.filter(approval_workflow_stage__approval_workflow=approval_workflow)
        )

        base_template = get_base_template(self.base_template, model)

        return render(
            request,
            "extras/object_approvalworkflow.html",
            {
                "object": obj,
                "verbose_name": helpers.bettertitle(obj._meta.verbose_name),
                "verbose_name_plural": obj._meta.verbose_name_plural,
                "approval_workflow": approval_workflow,
                "base_template": base_template,
                "active_tab": "approval_workflow",
                "default_time_zone": get_current_timezone(),
                "stage_table": stage_table,
                "response_table": response_table,
                "view_titles": self.get_view_titles(model=obj, view_type=""),
                "breadcrumbs": self.get_breadcrumbs(model=obj, view_type=""),
                "detail": True,
                **common_detail_view_context(request, obj),
            },
        )


#
# Computed Fields
#


class ComputedFieldUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.ComputedFieldBulkEditForm
    filterset_class = filters.ComputedFieldFilterSet
    filterset_form_class = forms.ComputedFieldFilterForm
    form_class = forms.ComputedFieldForm
    serializer_class = serializers.ComputedFieldSerializer
    table_class = tables.ComputedFieldTable
    queryset = ComputedField.objects.all()
    action_buttons = ("add",)
    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
                exclude_fields=["template"],
            ),
            object_detail.ObjectTextPanel(
                label="Template",
                section=SectionChoices.FULL_WIDTH,
                weight=100,
                object_field="template",
                render_as=object_detail.ObjectTextPanel.RenderOptions.CODE,
            ),
        ),
    )


#
# Config contexts
#

# TODO(Glenn): disallow (or at least warn) user from manually editing config contexts that
# have an associated owner, such as a Git repository


class ConfigContextUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.ConfigContextBulkEditForm
    filterset_class = filters.ConfigContextFilterSet
    filterset_form_class = forms.ConfigContextFilterForm
    form_class = forms.ConfigContextForm
    queryset = ConfigContext.objects.all()
    serializer_class = serializers.ConfigContextSerializer
    table_class = tables.ConfigContextTable

    class AssignmentObjectFieldsPanel(object_detail.ObjectFieldsPanel):
        def render_value(self, key, value, context):
            if key == "dynamic_groups" and not settings.CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED:
                return None
            if not value:
                return helpers.HTML_NONE

            items = []
            for val in value.all():
                rendered_val = helpers.hyperlinked_object(val)
                items.append(rendered_val)

            if not items:
                return helpers.HTML_NONE

            return format_html("<ul>{}</ul>", format_html_join("", "<li>{}</li>", ((item,) for item in items)))

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
                exclude_fields=[
                    "data",
                    "owner_content_type",
                    "owner_object_id",
                ],
                hide_if_unset=[
                    "owner",
                ],
            ),
            object_detail.Panel(
                weight=100,
                section=SectionChoices.FULL_WIDTH,
                label="Data",
                header_extra_content_template_path="extras/inc/configcontext_format.html",
                body_content_template_path="extras/inc/configcontext_data.html",
            ),
            AssignmentObjectFieldsPanel(
                weight=200,
                section=SectionChoices.RIGHT_HALF,
                label="Assignment",
                fields=[
                    "locations",
                    "roles",
                    "device_types",
                    "device_families",
                    "platforms",
                    "cluster_groups",
                    "clusters",
                    "tenant_groups",
                    "tenants",
                    "device_redundancy_groups",
                    "dynamic_groups",
                ],
            ),
        )
    )

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        # Determine user's preferred output format
        if request.GET.get("data_format") in ["json", "yaml"]:
            context["data_format"] = request.GET.get("data_format")
            if request.user.is_authenticated:
                request.user.set_config("extras.configcontext.format", context["data_format"], commit=True)
        elif request.user.is_authenticated:
            context["data_format"] = request.user.get_config("extras.configcontext.format", "json")
        else:
            context["data_format"] = "json"

        return context


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


class ConfigContextSchemaUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.ConfigContextSchemaBulkEditForm
    filterset_class = filters.ConfigContextSchemaFilterSet
    filterset_form_class = forms.ConfigContextSchemaFilterForm
    form_class = forms.ConfigContextSchemaForm
    queryset = ConfigContextSchema.objects.all()
    serializer_class = serializers.ConfigContextSchemaSerializer
    table_class = tables.ConfigContextSchemaTable

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        # Determine user's preferred output format
        if request.GET.get("data_format") in ["json", "yaml"]:
            context["data_format"] = request.GET.get("data_format")
            if request.user.is_authenticated:
                request.user.set_config("extras.configcontextschema.format", context["data_format"], commit=True)
        elif request.user.is_authenticated:
            context["data_format"] = request.user.get_config("extras.configcontextschema.format", "json")
        else:
            context["data_format"] = "json"

        return context


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

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
                value_transforms={
                    "address": [helpers.render_address],
                    "email": [helpers.hyperlinked_email],
                    "phone": [helpers.hyperlinked_phone_number],
                },
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                table_class=tables.TeamTable,
                table_filter="contacts",
                table_title="Assigned Teams",
                exclude_columns=["actions"],
                add_button_route=None,
            ),
            object_detail.ObjectsTablePanel(
                weight=200,
                section=SectionChoices.FULL_WIDTH,
                table_class=tables.ContactAssociationTable,
                table_filter="contact",
                table_title="Contact For",
                add_button_route=None,
                enable_related_link=False,
            ),
        ),
    )


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
    table_class = tables.AssociatedContactsTable
    non_filter_params = ("export", "page", "per_page", "sort")
    object_detail_content = None


class ObjectContactTeamMixin:
    """Mixin that contains a custom post() method to create a new contact/team and assign it to an existing object"""

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

                if isinstance(obj, Contact):
                    association = ContactAssociation(
                        contact=obj,
                        associated_object_type=ContentType.objects.get(id=request.POST.get("associated_object_type")),
                        associated_object_id=request.POST.get("associated_object_id"),
                        status=Status.objects.get(id=request.POST.get("status")),
                        role=Role.objects.get(id=request.POST.get("role")) if request.POST.get("role") else None,
                    )
                else:
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


class ObjectNewContactView(ObjectContactTeamMixin, generic.ObjectEditView):
    queryset = Contact.objects.all()
    model_form = forms.ObjectNewContactForm
    template_name = "extras/object_new_contact.html"


class ObjectNewTeamView(ObjectContactTeamMixin, generic.ObjectEditView):
    queryset = Team.objects.all()
    model_form = forms.ObjectNewTeamForm
    template_name = "extras/object_new_team.html"


class ObjectAssignContactOrTeamView(generic.ObjectEditView):
    queryset = ContactAssociation.objects.all()
    model_form = forms.ContactAssociationForm
    template_name = "extras/object_assign_contact_or_team.html"


#
# Custom fields
#


class CustomFieldUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.CustomFieldBulkEditForm
    queryset = CustomField.objects.all()
    serializer_class = serializers.CustomFieldSerializer
    filterset_class = filters.CustomFieldFilterSet
    filterset_form_class = forms.CustomFieldFilterForm
    form_class = forms.CustomFieldForm
    table_class = tables.CustomFieldTable
    template_name = "extras/customfield_update.html"
    action_buttons = ("add",)

    class CustomFieldObjectFieldsPanel(object_detail.ObjectFieldsPanel):
        def render_value(self, key, value, context):
            obj = get_obj_from_context(context, self.context_object_key)
            _type = getattr(obj, "type", None)

            if key == "default":
                if not value:
                    return helpers.HTML_NONE
                if _type == "markdown":
                    return helpers.render_markdown(value)
                elif _type == "json":
                    return helpers.render_json(value)
                else:
                    return helpers.placeholder(value)
            return super().render_value(key, value, context)

    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            CustomFieldObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
                exclude_fields=["content_types", "validation_minimum", "validation_maximum", "validation_regex"],
            ),
            object_detail.DataTablePanel(
                weight=200,
                section=SectionChoices.LEFT_HALF,
                label="Custom Field Choices",
                context_data_key="choices_data",
                context_columns_key="columns",
                context_column_headers_key="header",
            ),
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                label="Assignment",
                fields=[
                    "content_types",
                ],
                key_transforms={"content_types": "Content Types"},
            ),
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.RIGHT_HALF,
                weight=200,
                label="Validation Rules",
                fields=["validation_minimum", "validation_maximum", "validation_regex"],
                value_transforms={
                    "validation_regex": [lambda val: None if val == "" else val, helpers.pre_tag],
                },
            ),
        ]
    )

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        if self.action in ("create", "update"):
            if request.POST:
                context["choices"] = forms.CustomFieldChoiceFormSet(data=request.POST, instance=instance)
            else:
                context["choices"] = forms.CustomFieldChoiceFormSet(instance=instance)

        if self.action == "retrieve":
            choices_data = []

            for choice in instance.custom_field_choices.all():
                choices_data.append({"value": choice.value, "weight": choice.weight})

            context["columns"] = ["value", "weight"]
            context["header"] = ["Value", "Weight"]
            context["choices_data"] = choices_data

        return context

    def form_save(self, form, **kwargs):
        obj = super().form_save(form, **kwargs)

        # Process the formset for choices
        ctx = self.get_extra_context(self.request, obj)
        choices = ctx["choices"]
        if choices.is_valid():
            choices.save()
        else:
            raise ValidationError(choices.errors)

        return obj


#
# Custom Links
#
class CustomLinkUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.CustomLinkBulkEditForm
    filterset_class = filters.CustomLinkFilterSet
    filterset_form_class = forms.CustomLinkFilterForm
    form_class = forms.CustomLinkForm
    queryset = CustomLink.objects.all()
    serializer_class = serializers.CustomLinkSerializer
    table_class = tables.CustomLinkTable

    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            object_detail.ObjectFieldsPanel(
                label="Custom Link",
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=[
                    "content_type",
                    "name",
                    "group_name",
                    "weight",
                    "target_url",
                    "button_class",
                    "new_window",
                ],
                value_transforms={
                    "target_url": [helpers.pre_tag],
                    "button_class": [helpers.render_button_class],
                },
            ),
            object_detail.ObjectTextPanel(
                label="Text",
                section=SectionChoices.LEFT_HALF,
                weight=200,
                object_field="text",
                render_as=object_detail.ObjectTextPanel.RenderOptions.CODE,
            ),
        ]
    )


#
# Dynamic Groups
#


class DynamicGroupUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.DynamicGroupBulkEditForm
    filterset_class = filters.DynamicGroupFilterSet
    filterset_form_class = forms.DynamicGroupFilterForm
    form_class = forms.DynamicGroupForm
    queryset = DynamicGroup.objects.all()
    serializer_class = serializers.DynamicGroupSerializer
    table_class = tables.DynamicGroupTable
    action_buttons = ("add",)

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action in ("create", "update"):
            filterform_class = instance.generate_filter_form()
            if filterform_class is None:
                context["filter_form"] = None
            elif request.POST:
                context["filter_form"] = filterform_class(data=request.POST)
            else:
                initial = instance.get_initial()
                context["filter_form"] = filterform_class(initial=initial)

            formset_kwargs = {"instance": instance}
            if request.POST:
                formset_kwargs["data"] = request.POST
            context["children"] = forms.DynamicGroupMembershipFormSet(**formset_kwargs)

        elif self.action == "retrieve":
            model = instance.model
            table_class = get_table_for_model(model)
            members = instance.members
            if table_class is not None:
                if hasattr(members, "without_tree_fields"):
                    members = members.without_tree_fields()

                members_table = table_class(
                    members.restrict(request.user, "view"),
                    orderable=False,
                    exclude=["dynamic_group_count"],
                    hide_hierarchy_ui=True,
                )
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
                ancestors_table = tables.NestedDynamicGroupAncestorsTable(
                    ancestors,
                    orderable=False,
                )
                ancestors_tree = instance.flatten_ancestors_tree(instance.ancestors_tree())
                if instance.group_type != DynamicGroupTypeChoices.TYPE_STATIC:
                    context["raw_query"] = pretty_print_query(instance.generate_query())
                    context["members_list_url"] = None
                else:
                    context["raw_query"] = None
                    try:
                        context["members_list_url"] = reverse(get_route_for_model(instance.model, "list"))
                    except NoReverseMatch:
                        context["members_list_url"] = None

                context.update(
                    {
                        "members_verbose_name_plural": instance.model._meta.verbose_name_plural,
                        "members_table": members_table,
                        "ancestors_table": ancestors_table,
                        "ancestors_tree": ancestors_tree,
                        "descendants_table": descendants_table,
                        "descendants_tree": descendants_tree,
                    }
                )

        return context

    def form_save(self, form, commit=True, **kwargs):
        obj = form.save(commit=False)
        context = self.get_extra_context(self.request, obj)

        # Save filters
        if obj.group_type == DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER:
            filter_form = context.get("filter_form")
            if not filter_form or not filter_form.is_valid():
                form.add_error(None, "Errors encountered when saving Dynamic Group associations. See below.")
                raise ValidationError("invalid dynamic group filter_form")
            try:
                obj.set_filter(filter_form.cleaned_data)
            except ValidationError as err:
                form.add_error(None, "Invalid filter detected in existing DynamicGroup filter data.")
                for msg in getattr(err, "messages", [str(err)]):
                    if msg:
                        form.add_error(None, msg)
                raise

        if commit:
            # After filters have been set, now we save the object to the database.
            obj.save(update_cached_members=False)
            # Save m2m fields, such as Tags https://docs.djangoproject.com/en/3.2/topics/forms/modelforms/#the-save-method
            form.save_m2m()

            if obj.group_type != DynamicGroupTypeChoices.TYPE_STATIC:
                messages.warning(
                    self.request,
                    "Dynamic Group membership is not automatically recalculated after creating/editing the group, "
                    'as it may take some time to complete. You can use the "Refresh Members" button when ready.',
                )

        # Process the formsets for children
        children = context.get("children")
        if children and not children.is_valid():
            form.add_error(None, "Errors encountered when saving Dynamic Group associations. See below.")
            # dedupe only non-field errors to avoid duplicates in the banner
            added_errors = set()
            for f in children.forms:
                for msg in f.non_field_errors():
                    if msg not in added_errors:
                        form.add_error(None, msg)
                        added_errors.add(msg)
            raise ValidationError("invalid DynamicGroupMembershipFormSet")

        if commit and children:
            children.save()

        return obj

    # Suppress the global top banner when ValidationError happens
    def _handle_validation_error(self, e):
        self.has_error = True

    @action(
        detail=False,
        methods=["GET", "POST"],
        url_path="assign-members",
        url_name="bulk_assign",
        custom_view_base_action="add",
        custom_view_additional_permissions=[
            "extras.add_staticgroupassociation",
        ],
    )
    def bulk_assign(self, request):
        """
        Update the static group assignments of the provided `pk_list` (or `_all`) of the given `content_type`.

        Unlike BulkEditView, this takes a single POST rather than two to perform its operation as
        there's no separate confirmation step involved.
        """
        if request.method == "GET":
            return redirect(reverse("extras:staticgroupassociation_list"))

        # TODO more error handling - content-type doesn't exist, model_class not found, filterset missing, etc.
        content_type = ContentType.objects.get(pk=request.POST.get("content_type"))
        model = content_type.model_class()
        self.default_return_url = get_route_for_model(model, "list")
        filterset_class = get_filterset_for_model(model)

        if request.POST.get("_all"):
            if filterset_class:
                pk_list = list(filterset_class(request.GET, model.objects.only("pk")).qs.values_list("pk", flat=True))
            else:
                pk_list = list(model.objects.values_list("pk", flat=True))
        else:
            pk_list = request.POST.getlist("pk")

        form = forms.DynamicGroupBulkAssignForm(model, request.POST)
        restrict_form_fields(form, request.user)

        if form.is_valid():
            logger.debug("Form validation was successful")
            try:
                with transaction.atomic():
                    add_to_groups = list(form.cleaned_data["add_to_groups"])
                    new_group_name = form.cleaned_data["create_and_assign_to_new_group_name"]
                    if new_group_name:
                        if not request.user.has_perm("extras.add_dynamicgroup"):
                            raise DynamicGroup.DoesNotExist
                        else:
                            new_group = DynamicGroup(
                                name=new_group_name,
                                content_type=content_type,
                                group_type=DynamicGroupTypeChoices.TYPE_STATIC,
                            )
                            new_group.validated_save()
                            # Check permissions
                            DynamicGroup.objects.restrict(request.user, "add").get(pk=new_group.pk)

                            add_to_groups.append(new_group)
                            msg = "Created dynamic group"
                            logger.info(f"{msg} {new_group} (PK: {new_group.pk})")
                            msg = format_html('{} <a href="{}">{}</a>', msg, new_group.get_absolute_url(), new_group)
                            messages.success(request, msg)

                    with deferred_change_logging_for_bulk_operation():
                        associations = []
                        for pk in pk_list:
                            for dynamic_group in add_to_groups:
                                association, created = StaticGroupAssociation.objects.get_or_create(
                                    dynamic_group=dynamic_group,
                                    associated_object_type_id=content_type.id,
                                    associated_object_id=pk,
                                )
                                association.validated_save()
                                associations.append(association)
                                if created:
                                    logger.debug("Created %s", association)

                        # Enforce object-level permissions
                        permitted_associations = StaticGroupAssociation.objects.restrict(request.user, "add")
                        if permitted_associations.filter(pk__in=[assoc.pk for assoc in associations]).count() != len(
                            associations
                        ):
                            raise StaticGroupAssociation.DoesNotExist

                    if associations:
                        msg = (
                            f"Added {len(pk_list)} {model._meta.verbose_name_plural} "
                            f"to {len(add_to_groups)} dynamic group(s)."
                        )
                        logger.info(msg)
                        messages.success(request, msg)

                    if form.cleaned_data["remove_from_groups"]:
                        for dynamic_group in form.cleaned_data["remove_from_groups"]:
                            (
                                StaticGroupAssociation.objects.restrict(request.user, "delete")
                                .filter(
                                    dynamic_group=dynamic_group,
                                    associated_object_type=content_type,
                                    associated_object_id__in=pk_list,
                                )
                                .delete()
                            )

                        msg = (
                            f"Removed {len(pk_list)} {model._meta.verbose_name_plural} from "
                            f"{len(form.cleaned_data['remove_from_groups'])} dynamic group(s)."
                        )
                        logger.info(msg)
                        messages.success(request, msg)
            except ValidationError as e:
                messages.error(request, e)
            except ObjectDoesNotExist:
                msg = "Static group association failed due to object-level permissions violation"
                logger.warning(msg)
                messages.error(request, msg)

        else:
            logger.debug("Form validation failed")
            messages.error(request, form.errors)

        return redirect(self.get_return_url(request))


class ObjectDynamicGroupsView(generic.GenericView):
    """
    Present a list of dynamic groups associated to a particular object.

    Note that this isn't currently widely used, as most object detail views currently render the table inline
    rather than using this separate view. This may change in the future.

    base_template: Specify to explicitly identify the base object detail template to render.
        If not provided, "<app>/<model>.html", "<app>/<model>_retrieve.html", or "generic/object_retrieve.html"
        will be used, as per `get_base_template()`.
    """

    base_template: Optional[str] = None

    def get(self, request, model, **kwargs):
        # Handle QuerySet restriction of parent object if needed
        if hasattr(model.objects, "restrict"):
            obj = get_object_or_404(model.objects.restrict(request.user, "view"), **kwargs)
        else:
            obj = get_object_or_404(model, **kwargs)

        # Gather all dynamic groups for this object (and its related objects)
        dynamicgroups_table = tables.DynamicGroupTable(
            data=obj.dynamic_groups.restrict(request.user, "view"), orderable=False
        )
        dynamicgroups_table.columns.hide("content_type")

        # Apply the request context
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(dynamicgroups_table)

        base_template = get_base_template(self.base_template, model)

        return render(
            request,
            "extras/object_dynamicgroups.html",
            {
                "object": obj,
                "verbose_name": obj._meta.verbose_name,
                "verbose_name_plural": obj._meta.verbose_name_plural,
                "table": dynamicgroups_table,
                "base_template": base_template,
                "active_tab": "dynamic-groups",
                "view_titles": self.get_view_titles(model=obj, view_type=""),
                "breadcrumbs": self.get_breadcrumbs(model=obj, view_type=""),
                "detail": True,
            },
        )


#
# Export Templates
#


class ExportTemplateUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.ExportTemplateBulkEditForm
    filterset_class = filters.ExportTemplateFilterSet
    filterset_form_class = forms.ExportTemplateFilterForm
    form_class = forms.ExportTemplateForm
    queryset = ExportTemplate.objects.all()
    serializer_class = serializers.ExportTemplateSerializer
    table_class = tables.ExportTemplateTable

    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            object_detail.ObjectFieldsPanel(
                label="Details",
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=["name", "owner", "description"],
            ),
            object_detail.ObjectFieldsPanel(
                label="Template",
                section=SectionChoices.LEFT_HALF,
                weight=200,
                fields=["content_type", "mime_type", "file_extension"],
            ),
            object_detail.ObjectTextPanel(
                label="Code Template",
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                object_field="template_code",
                render_as=object_detail.ObjectTextPanel.RenderOptions.CODE,
            ),
        ]
    )


#
# External integrations
#


class ExternalIntegrationUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.ExternalIntegrationBulkEditForm
    filterset_class = filters.ExternalIntegrationFilterSet
    filterset_form_class = forms.ExternalIntegrationFilterForm
    form_class = forms.ExternalIntegrationForm
    queryset = ExternalIntegration.objects.select_related("secrets_group")
    serializer_class = serializers.ExternalIntegrationSerializer
    table_class = tables.ExternalIntegrationTable

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                # Default ordering with __all__ leaves something to be desired
                fields=[
                    "name",
                    "remote_url",
                    "http_method",
                    "headers",
                    "verify_ssl",
                    "ca_file_path",
                    "secrets_group",
                    "timeout",
                    "extra_config",
                ],
            ),
        ),
    )


#
# Git repositories
#


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
        return redirect(reverse("extras:gitrepository", args=(pk,)), permanent=False)
    else:
        repository = get_object_or_404(GitRepository.objects.restrict(request.user, "change"), pk=pk)
        job_result = func(repository, request.user)

    return redirect(job_result.get_absolute_url())


class GitRepositoryUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.GitRepositoryBulkEditForm
    filterset_form_class = forms.GitRepositoryFilterForm
    queryset = GitRepository.objects.all()
    form_class = forms.GitRepositoryForm
    filterset_class = filters.GitRepositoryFilterSet
    serializer_class = serializers.GitRepositorySerializer
    table_class = tables.GitRepositoryTable
    view_titles = Titles(titles={"result": "{{ object.display|default:object }} - Synchronization Status"})

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        context["datasource_contents"] = get_datasource_contents("extras.gitrepository")

        if self.action in ("list", "bulk_update", "bulk_destroy"):
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
            context["job_results"] = results

        return context

    def form_valid(self, form):
        if hasattr(form, "instance") and form.instance is not None:
            form.instance.user = self.request.user
            form.instance.request = self.request
        return super().form_valid(form)

    def get_return_url(self, request, obj=None, default_return_url=None):
        # Only redirect to result if object exists and action is not deletion
        if request.method == "POST" and obj is not None and self.action != "destroy":
            return reverse("extras:gitrepository_result", kwargs={"pk": obj.pk})
        return super().get_return_url(request, obj=obj, default_return_url=default_return_url)

    @action(
        detail=True,
        url_path="result",
        url_name="result",
        custom_view_base_action="view",
    )
    def result(self, request, pk=None):
        instance = self.get_object()
        job_result = instance.get_latest_sync()

        context = {
            **super().get_extra_context(request, instance),
            "result": job_result or {},
            "base_template": "extras/gitrepository_retrieve.html",
            "object": instance,
            "active_tab": "result",
            "verbose_name": instance._meta.verbose_name,
        }

        return Response(
            context,
            template_name="extras/gitrepository_result.html",
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="sync",
        url_name="sync",
        custom_view_base_action="change",
        custom_view_additional_permissions=["extras.change_gitrepository"],
    )
    def sync(self, request, pk=None):
        return check_and_call_git_repository_function(request, pk, enqueue_pull_git_repository_and_refresh_data)

    @action(
        detail=True,
        methods=["post"],
        url_path="dry-run",
        url_name="dryrun",
        custom_view_base_action="change",
        custom_view_additional_permissions=["extras.change_gitrepository"],
    )
    def dry_run(self, request, pk=None):
        return check_and_call_git_repository_function(request, pk, enqueue_git_repository_diff_origin_and_local)


#
# Saved GraphQL queries
#


class GraphQLQueryUIViewSet(
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectEditViewMixin,
    ObjectDestroyViewMixin,
    ObjectBulkDestroyViewMixin,
    ObjectChangeLogViewMixin,
    ObjectDataComplianceViewMixin,
    ObjectNotesViewMixin,
):
    filterset_form_class = forms.GraphQLQueryFilterForm
    queryset = GraphQLQuery.objects.all()
    form_class = forms.GraphQLQueryForm
    filterset_class = filters.GraphQLQueryFilterSet
    serializer_class = serializers.GraphQLQuerySerializer
    table_class = tables.GraphQLQueryTable
    action_buttons = ("add",)

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                label="Query",
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=["name", "query", "variables"],
                value_transforms={
                    "query": [lambda val: format_html('<pre><code class="language-graphql">{}</code></pre>', val)],
                    "variables": [lambda val: helpers.render_json(val, syntax_highlight=True, pretty_print=True)],
                },
            ),
            object_detail.Panel(
                weight=100,
                section=object_detail.SectionChoices.RIGHT_HALF,
                body_content_template_path="extras/inc/graphqlquery_execute.html",
                body_wrapper_template_path="components/panel/body_wrapper_table.html",
            ),
        )
    )


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

    def alter_obj(self, obj, request, url_args, url_kwargs):
        if not obj.present_in_database:
            # Assign the parent object based on URL kwargs
            model = url_kwargs.get("model")
            if "object_id" in url_kwargs:
                obj.parent = get_object_or_404(model, pk=url_kwargs["object_id"])
            elif "slug" in url_kwargs:
                obj.parent = get_object_or_404(model, slug=url_kwargs["slug"])
            else:
                raise RuntimeError("Neither object_id nor slug were provided?")
        return obj

    def get_return_url(self, request, obj=None, default_return_url=None):
        return obj.parent.get_absolute_url()


class ImageAttachmentDeleteView(generic.ObjectDeleteView):
    queryset = ImageAttachment.objects.all()

    def get_return_url(self, request, obj=None, default_return_url=None):
        return obj.parent.get_absolute_url()


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
    non_filter_params = (
        *generic.ObjectListView.non_filter_params,
        "display",
    )
    template_name = "extras/job_list.html"

    def alter_queryset(self, request):
        queryset = super().alter_queryset(request)
        # Default to hiding "hidden" and non-installed jobs
        filter_params = self.get_filter_params(request)
        if "hidden" not in filter_params:
            queryset = queryset.filter(hidden=False)
        if "installed" not in filter_params:
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

    def _handle_approval_workflow_response(self, request, scheduled_job, return_url):
        """Handle response for jobs requiring approval workflow."""
        messages.success(request, f"Job '{scheduled_job.name}' successfully submitted for approval")
        return redirect(return_url or reverse("extras:scheduledjob_approvalworkflow", args=[scheduled_job.pk]))

    def _handle_scheduled_job_response(self, request, scheduled_job, return_url):
        """Handle response for successfully scheduled jobs."""
        messages.success(request, f"Job {scheduled_job.name} successfully scheduled")
        return redirect(return_url or "extras:scheduledjob_list")

    def _handle_immediate_execution(
        self, request, job_model, job_class, job_form, profile, ignore_singleton_lock, job_queue, return_url
    ):
        """Handle immediate job execution."""
        job_kwargs = job_class.prepare_job_kwargs(job_form.cleaned_data)
        job_result = JobResult.enqueue_job(
            job_model,
            request.user,
            profile=profile,
            ignore_singleton_lock=ignore_singleton_lock,
            job_queue=job_queue,
            **job_class.serialize_data(job_kwargs),
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

    def get(self, request, class_path=None, pk=None):
        job_model = self._get_job_model_or_404(class_path, pk)

        try:
            job_class = get_job(job_model.class_path, reload=True)
            if job_class is None:
                raise RuntimeError("Job code for this job is not currently installed or loadable")
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
                    job_queue = None
                    if task_queue is not None:
                        try:
                            job_queue = JobQueue.objects.get(
                                name=task_queue, queue_type=JobQueueTypeChoices.TYPE_CELERY
                            )
                        except JobQueue.DoesNotExist:
                            pass
                    initial["_job_queue"] = job_queue
                    initial["_profile"] = job_result.celery_kwargs.get("nautobot_job_profile", False)
                    initial["_ignore_singleton_lock"] = job_result.celery_kwargs.get(
                        "nautobot_job_ignore_singleton_lock", False
                    )
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
                    messages.error(
                        request, f'Unable to render requested custom job template "{job_class.template_name}": {err}'
                    )
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

        job_class = get_job(job_model.class_path, reload=True)
        job_form = job_class.as_form(request.POST, request.FILES) if job_class is not None else None
        schedule_form = forms.JobScheduleForm(request.POST)

        return_url = request.POST.get("_return_url")
        if return_url is not None and url_has_allowed_host_and_scheme(url=return_url, allowed_hosts=request.get_host()):
            return_url = iri_to_uri(return_url)
        else:
            return_url = None

        # Allow execution only if the job is runnable.
        if not job_model.installed or job_class is None:
            messages.error(request, "Unable to run or schedule job: Job is not presently installed.")
        elif not job_model.enabled:
            messages.error(request, "Unable to run or schedule job: Job is not enabled to be run.")
        elif (
            job_model.has_sensitive_variables
            and request.POST.get("_schedule_type") != JobExecutionType.TYPE_IMMEDIATELY
        ):
            messages.error(request, "Unable to schedule job: Job may have sensitive input variables.")
        elif job_form is not None and job_form.is_valid() and schedule_form.is_valid():
            job_queue = job_form.cleaned_data.pop("_job_queue", None)
            if job_queue is None:
                job_queue = job_model.default_job_queue

            if job_queue.queue_type == JobQueueTypeChoices.TYPE_CELERY and not get_worker_count(queue=job_queue):
                messages.warning(
                    request,
                    format_html(
                        "No celery workers found for queue {}, job may never run unless a worker is started.",
                        job_queue,
                    ),
                )

            dryrun = job_form.cleaned_data.get("dryrun", False)
            # Run the job. A new JobResult is created.
            profile = job_form.cleaned_data.pop("_profile")
            ignore_singleton_lock = job_form.cleaned_data.pop("_ignore_singleton_lock", False)
            schedule_type = schedule_form.cleaned_data["_schedule_type"]

            with transaction.atomic():
                scheduled_job = ScheduledJob.create_schedule(
                    job_model,
                    request.user,
                    name=schedule_form.cleaned_data.get("_schedule_name"),
                    start_time=schedule_form.cleaned_data.get("_schedule_start_time"),
                    interval=schedule_type,
                    crontab=schedule_form.cleaned_data.get("_recurrence_custom_time"),
                    job_queue=job_queue,
                    profile=profile,
                    ignore_singleton_lock=ignore_singleton_lock,
                    **job_class.serialize_data(job_form.cleaned_data),
                )
                scheduled_job_has_approval_workflow = scheduled_job.has_approval_workflow_definition()
                is_scheduled = schedule_type in JobExecutionType.SCHEDULE_CHOICES
                if job_model.has_sensitive_variables and scheduled_job_has_approval_workflow:
                    messages.error(
                        request,
                        "Unable to run or schedule job: "
                        "This job is flagged as possibly having sensitive variables but also has an applicable approval workflow definition."
                        "Modify or remove the approval workflow definition or modify the job to set `has_sensitive_variables` to False.",
                    )
                    scheduled_job.delete()
                    scheduled_job = None
                else:
                    if dryrun and not is_scheduled:
                        # Enqueue job for immediate execution when dryrun and (no schedule, no has_sensitive_variables)
                        scheduled_job.delete()
                        scheduled_job = None
                        return self._handle_immediate_execution(
                            request,
                            job_model,
                            job_class,
                            job_form,
                            profile,
                            ignore_singleton_lock,
                            job_queue,
                            return_url,
                        )
                    # Step 1: Check if approval is required
                    if scheduled_job_has_approval_workflow:
                        return self._handle_approval_workflow_response(request, scheduled_job, return_url)

                    # Step 3: If approval is not required
                    if is_scheduled:
                        return self._handle_scheduled_job_response(request, scheduled_job, return_url)

                    # Step 4: Immediate execution (no schedule, no approval)
                    scheduled_job.delete()
                    scheduled_job = None
                    return self._handle_immediate_execution(
                        request,
                        job_model,
                        job_class,
                        job_form,
                        profile,
                        ignore_singleton_lock,
                        job_queue,
                        return_url,
                    )

        if return_url:
            return redirect(return_url)

        template_name = "extras/job.html"
        if job_class is not None and hasattr(job_class, "template_name"):
            try:
                get_template(job_class.template_name)
                template_name = job_class.template_name
            except TemplateDoesNotExist as err:
                messages.error(
                    request, f'Unable to render requested custom job template "{job_class.template_name}": {err}'
                )

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
    template_name = "generic/object_retrieve.html"
    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                label="Source Code",
                fields=[
                    "module_name",
                    "job_class_name",
                    "class_path",
                    "installed",
                    "is_job_hook_receiver",
                    "is_job_button_receiver",
                ],
            ),
            jobs_ui.JobObjectFieldsPanel(
                weight=200,
                section=SectionChoices.LEFT_HALF,
                label="Job",
                fields=["grouping", "name", "description", "enabled"],
                value_transforms={
                    "description": [helpers.render_markdown],
                },
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                section=SectionChoices.FULL_WIDTH,
                table_class=tables.JobResultTable,
                table_title="Job Results",
                table_filter="job_model",
                exclude_columns=["name", "job_model"],
            ),
            jobs_ui.JobObjectFieldsPanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                label="Properties",
                fields=[
                    "supports_dryrun",
                    "dryrun_default",
                    "read_only",
                    "hidden",
                    "has_sensitive_variables",
                    "is_singleton",
                    "soft_time_limit",
                    "time_limit",
                    "job_queues",
                    "default_job_queue",
                ],
            ),
        ],
        extra_buttons=[
            jobs_ui.JobRunScheduleButton(
                weight=100,
                link_name="extras:job_run",
                label="Run/Schedule",
                icon="mdi-play",
                color=ButtonActionColorChoices.SUBMIT,
                required_permissions=["extras.job_run"],
            ),
        ],
    )


class JobEditView(generic.ObjectEditView):
    queryset = JobModel.objects.all()
    model_form = forms.JobEditForm
    template_name = "extras/job_edit.html"

    def alter_obj(self, obj, request, url_args, url_kwargs):
        # Reload the job class to ensure we have the latest version
        get_job(obj.class_path, reload=True)
        return obj


class JobBulkEditView(generic.BulkEditView):
    queryset = JobModel.objects.all()
    filterset = filters.JobFilterSet
    table = tables.JobTable
    form = forms.JobBulkEditForm
    template_name = "extras/job_bulk_edit.html"


class JobDeleteView(generic.ObjectDeleteView):
    queryset = JobModel.objects.all()


class JobBulkDeleteView(generic.BulkDeleteView):
    queryset = JobModel.objects.all()
    filterset = filters.JobFilterSet
    table = tables.JobTable


class JobQueueUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.JobQueueBulkEditForm
    filterset_form_class = forms.JobQueueFilterForm
    queryset = JobQueue.objects.all()
    form_class = forms.JobQueueForm
    filterset_class = filters.JobQueueFilterSet
    serializer_class = serializers.JobQueueSerializer
    table_class = tables.JobQueueTable

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "name",
                    "queue_type",
                    "description",
                    "tenant",
                ],
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                section=SectionChoices.FULL_WIDTH,
                table_title="Assigned Jobs",
                table_class=tables.JobTable,
                table_filter="job_queues",
            ),
        )
    )


#
# Saved Views
#


class SavedViewUIViewSet(
    ObjectDetailViewMixin,
    ObjectChangeLogViewMixin,
    ObjectDestroyViewMixin,
    ObjectEditViewMixin,
    ObjectListViewMixin,
):
    queryset = SavedView.objects.all()
    form_class = forms.SavedViewForm
    filterset_class = filters.SavedViewFilterSet
    serializer_class = serializers.SavedViewSerializer
    table_class = tables.SavedViewTable
    action_buttons = ("export",)
    permission_classes = [
        IsAuthenticated,
    ]

    def alter_queryset(self, request):
        """
        Two scenarios we need to handle here:
        1. User can view all saved views with extras.view_savedview permission.
        2. User without the permission can only view shared savedviews and his/her own saved views.
        """
        queryset = super().alter_queryset(request)
        user = request.user
        if user.has_perms(["extras.view_savedview"]):
            saved_views = queryset.restrict(user, "view")
        else:
            shared_saved_views = queryset.filter(is_shared=True)
            user_owned_saved_views = queryset.filter(owner=user)
            saved_views = shared_saved_views | user_owned_saved_views
        return saved_views

    def get_queryset(self):
        """
        Get the list of items for this view.
        All users should be able to see saved views so we do not apply extra permissions.
        """
        return self.queryset.all()

    def check_permissions(self, request):
        """
        Override this method to not check any nautobot-specific object permissions and to only check if the user is authenticated.
        Since users with <app_label>.view_<model_name> permissions should be able to view saved views related to this model.
        And those permissions will be enforced in the related view.
        """
        for permission in self.get_permissions():
            if not permission.has_permission(request, self):
                self.permission_denied(
                    request, message=getattr(permission, "message", None), code=getattr(permission, "code", None)
                )

    def extra_message_context(self, obj):
        """
        Context variables for this extra message.
        """
        return {"new_global_default_view": obj}

    def extra_message(self, **kwargs):
        new_global_default_view = kwargs.get("new_global_default_view")
        view_name = new_global_default_view.view
        message = ""
        if new_global_default_view.is_global_default:
            message = format_html(
                '<br>The global default saved view for "{}" is set to <a href="{}">{}</a>',
                view_name,
                new_global_default_view.get_absolute_url(),
                new_global_default_view.name,
            )
        return message

    def list(self, request, *args, **kwargs):
        if not request.user.has_perms(["extras.view_savedview"]):
            return self.handle_no_permission()
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        The detail view for a saved view should the related ObjectListView with saved configurations applied
        """
        instance = self.get_object()
        list_view_url = reverse(instance.view) + f"?saved_view={instance.pk}"
        return redirect(list_view_url)

    @action(detail=True, name="Set Default", methods=["get"], url_path="set-default", url_name="set_default")
    def set_default(self, request, *args, **kwargs):
        """
        Set current saved view as the the request.user default view. Overriding the global default view if there is one.
        """
        user = request.user
        sv = SavedView.objects.get(pk=kwargs.get("pk", None))
        UserSavedViewAssociation.objects.filter(user=user, view_name=sv.view).delete()
        UserSavedViewAssociation.objects.create(user=user, saved_view=sv, view_name=sv.view)
        list_view_url = sv.get_absolute_url()
        messages.success(
            request, f"Successfully set current view '{sv.name}' as the default '{sv.view}' view for user {user}"
        )
        return redirect(list_view_url)

    @action(detail=True, name="Update Config", methods=["get"], url_path="update-config", url_name="update_config")
    def update_saved_view_config(self, request, *args, **kwargs):
        """
        Extract filter_params, pagination and sort_order from request.GET and apply it to the SavedView specified
        """
        sv = SavedView.objects.get(pk=kwargs.get("pk", None))
        if sv.owner == request.user or request.user.has_perms(["extras.change_savedview"]):
            pass
        else:
            messages.error(
                request, f"You do not have the required permission to modify this Saved View owned by {sv.owner}"
            )
            return redirect(self.get_return_url(request, obj=sv))
        table_changes_pending = request.GET.get("table_changes_pending", False)
        all_filters_removed = request.GET.get("all_filters_removed", False)
        pagination_count = request.GET.get("per_page", None)
        if pagination_count is not None:
            sv.config["pagination_count"] = int(pagination_count)
        sort_order = request.GET.getlist("sort", [])
        if sort_order:
            sv.config["sort_order"] = sort_order

        model = get_model_for_view_name(sv.view)
        filterset_class = get_filterset_for_model(model)
        filterset = filterset_class()
        filter_params = {}
        for key in request.GET:
            if key in self.non_filter_params:
                continue
            try:
                if is_single_choice_field(filterset, key):
                    filter_params[key] = request.GET.getlist(key)[0]
            except FilterSetFieldNotFound:
                continue
            try:
                if not is_single_choice_field(filterset, key):
                    filter_params[key] = request.GET.getlist(key)
            except FilterSetFieldNotFound:
                continue

        if filter_params:
            sv.config["filter_params"] = filter_params
        elif all_filters_removed:
            sv.config["filter_params"] = {}

        if table_changes_pending:
            table_class = get_table_class_string_from_view_name(sv.view)
            if table_class:
                if sv.config.get("table_config", None) is None:
                    sv.config["table_config"] = {}
                sv.config["table_config"][f"{table_class}"] = request.user.get_config(f"tables.{table_class}")

        sv.validated_save()
        list_view_url = sv.get_absolute_url()
        messages.success(request, f"Successfully updated current view {sv.name}")
        return redirect(list_view_url)

    def create(self, request, *args, **kwargs):
        """
        This method will extract filter_params, pagination and sort_order from request.GET
        and the name of the new SavedView from request.POST to create a new SavedView.
        """
        name = request.POST.get("name")
        view_name = request.POST.get("view")
        is_shared = request.POST.get("is_shared", False)
        if is_shared:
            is_shared = True
        params = request.POST.get("params", "")
        param_dict = fixup_filterset_query_params(parse_qs(params), view_name, self.non_filter_params)

        single_value_params = ["saved_view", "table_changes_pending", "all_filters_removed", "per_page"]
        for key in param_dict.keys():
            if key in single_value_params:
                param_dict[key] = param_dict[key][0]

        derived_view_pk = param_dict.get("saved_view", None)
        derived_instance = None
        if derived_view_pk:
            derived_instance = self.get_queryset().get(pk=derived_view_pk)
        try:
            reverse(view_name)
        except NoReverseMatch:
            messages.error(request, f"Invalid view name {view_name} specified.")
            if derived_view_pk:
                return redirect(self.get_return_url(request, obj=derived_instance))
            else:
                return redirect(self.get_return_url(request))
        table_changes_pending = param_dict.get("table_changes_pending", False)
        all_filters_removed = param_dict.get("all_filters_removed", False)
        try:
            sv = SavedView.objects.create(name=name, owner=request.user, view=view_name, is_shared=is_shared)
        except IntegrityError:
            messages.error(request, f"You already have a Saved View named '{name}' for this view '{view_name}'")
            if derived_view_pk:
                return redirect(self.get_return_url(request, obj=derived_instance))
            else:
                return redirect(reverse(view_name))
        pagination_count = param_dict.get("per_page", None)
        if not pagination_count:
            if derived_instance and derived_instance.config.get("pagination_count", None):
                pagination_count = derived_instance.config["pagination_count"]
            else:
                pagination_count = get_settings_or_config("PAGINATE_COUNT", fallback=PAGINATE_COUNT_DEFAULT)
        sv.config["pagination_count"] = int(pagination_count)
        sort_order = param_dict.get("sort", [])
        if not sort_order:
            if derived_instance:
                sort_order = derived_instance.config.get("sort_order", [])
        sv.config["sort_order"] = sort_order

        sv.config["filter_params"] = {}
        for key in param_dict:
            if key in [*self.non_filter_params, "view"]:
                continue
            sv.config["filter_params"][key] = param_dict.get(key)
        if not sv.config["filter_params"]:
            if derived_instance and all_filters_removed:
                sv.config["filter_params"] = {}
            elif derived_instance:
                sv.config["filter_params"] = derived_instance.config["filter_params"]

        table_class = get_table_class_string_from_view_name(view_name)
        sv.config["table_config"] = {}
        if table_class:
            if table_changes_pending or derived_instance is None:
                sv.config["table_config"][f"{table_class}"] = request.user.get_config(f"tables.{table_class}")
            elif derived_instance.config.get("table_config") and derived_instance.config["table_config"].get(
                f"{table_class}"
            ):
                sv.config["table_config"][f"{table_class}"] = derived_instance.config["table_config"][f"{table_class}"]
        try:
            sv.validated_save()
            list_view_url = sv.get_absolute_url()
            message = f"Successfully created new Saved View '{sv.name}'."
            messages.success(request, message)
            return redirect(list_view_url)
        except ValidationError as e:
            messages.error(request, e)
            return redirect(self.get_return_url(request))

    def destroy(self, request, *args, **kwargs):
        """
        request.GET: render the ObjectDeleteConfirmationForm which is passed to NautobotHTMLRenderer as Response.
        request.POST: call perform_destroy() which validates the form and perform the action of delete.
        Override to add more variables to Response
        """
        sv = SavedView.objects.get(pk=kwargs.get("pk", None))
        if sv.owner == request.user or request.user.has_perms(["extras.delete_savedview"]):
            pass
        else:
            messages.error(
                request, f"You do not have the required permission to delete this Saved View owned by {sv.owner}"
            )
            return redirect(self.get_return_url(request, obj=sv))
        return super().destroy(request, *args, **kwargs)


class ScheduledJobListView(generic.ObjectListView):
    queryset = ScheduledJob.objects.all()
    table = tables.ScheduledJobTable
    filterset = filters.ScheduledJobFilterSet
    filterset_form = forms.ScheduledJobFilterForm
    action_buttons = ()


class ScheduledJobBulkDeleteView(generic.BulkDeleteView):
    queryset = ScheduledJob.objects.all()
    table = tables.ScheduledJobTable
    filterset = filters.ScheduledJobFilterSet


class ScheduledJobView(generic.ObjectView):
    queryset = ScheduledJob.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        # Add job class labels
        job_class = get_job(instance.task)
        labels = {}
        if job_class is not None:
            for name, var in job_class._get_vars().items():
                field = var.as_field()
                labels[name] = field.label or pretty_name(name)

        context.update(
            {
                "labels": labels,
                "job_class_found": (job_class is not None),
                "default_time_zone": get_current_timezone(),
            }
        )

        # Add approval workflow table
        approval_workflows = instance.associated_approval_workflows.all()
        approval_workflows_count = approval_workflows.count()
        approval_workflow_table = tables.ApprovalWorkflowTable(
            data=approval_workflows,
            user=request.user,
            exclude=["object_under_review", "object_under_review_content_type"],
        )

        RequestConfig(
            request, paginate={"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        ).configure(approval_workflow_table)

        context.update(
            {
                "approval_workflows_count": approval_workflows_count,
                "approval_workflow_table": approval_workflow_table,
            }
        )

        return context


class ScheduledJobDeleteView(generic.ObjectDeleteView):
    queryset = ScheduledJob.objects.all()


#
# Job hooks
#


class JobHookUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.JobHookBulkEditForm
    filterset_class = filters.JobHookFilterSet
    filterset_form_class = forms.JobHookFilterForm
    form_class = forms.JobHookForm
    serializer_class = serializers.JobHookSerializer
    table_class = tables.JobHookTable
    queryset = JobHook.objects.all()

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
        )
    )


#
# JobResult
#


class JobResultUIViewSet(
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectDestroyViewMixin,
    ObjectBulkDestroyViewMixin,
):
    filterset_class = filters.JobResultFilterSet
    filterset_form_class = forms.JobResultFilterForm
    serializer_class = serializers.JobResultSerializer
    table_class = tables.JobResultTable
    queryset = JobResult.objects.all()
    action_buttons = ()
    breadcrumbs = Breadcrumbs(
        items={
            "detail": [
                ModelBreadcrumbItem(),
                # if result.job_model is not None
                BaseBreadcrumbItem(
                    label=context_object_attr("job_model.grouping", context_key="result"),
                    should_render=lambda c: c["result"].job_model is not None,
                ),
                InstanceParentBreadcrumbItem(
                    instance_key="result",
                    parent_key="job_model",
                    parent_lookup_key="name",
                    should_render=lambda c: c["result"].job_model is not None,
                ),
                # elif job in context
                ViewNameBreadcrumbItem(
                    view_name="extras:jobresult_list",
                    label=context_object_attr("class_path", context_key="job"),
                    reverse_query_params=lambda c: {"name": urlencode(c["job"].class_path)},
                    should_render=lambda c: c["result"].job_model is None and c["job"] is not None,
                ),
                # else
                BaseBreadcrumbItem(
                    label=context_object_attr("name", context_key="result"),
                    should_render=lambda c: c["result"].job_model is None and c["job"] is None,
                ),
            ]
        },
        detail_item_label=context_object_attr("date_created"),
    )

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            job_class = None
            if instance and instance.job_model:
                job_class = instance.job_model.job_class

            context.update(
                {
                    "job": job_class,
                    "associated_record": None,
                    "result": instance,
                }
            )

        return context

    def get_queryset(self):
        queryset = super().get_queryset().select_related("job_model", "user")

        if not self.detail:
            queryset = queryset.defer("result", "task_args", "task_kwargs", "celery_kwargs", "traceback", "meta")

        return queryset

    @action(
        detail=True,
        url_path="log-table",
        url_name="log-table",
        custom_view_base_action="view",
    )
    def log_table(self, request, pk=None):
        """
        Custom action to return a rendered JobLogEntry table for a JobResult.
        """

        instance = get_object_or_404(self.queryset.restrict(request.user, "view"), pk=pk)

        filter_q = request.GET.get("q")
        if filter_q:
            queryset = instance.job_log_entries.filter(
                Q(message__icontains=filter_q) | Q(log_level__icontains=filter_q)
            )
        else:
            queryset = instance.job_log_entries.all()

        log_table = tables.JobLogEntryTable(data=queryset, user=request.user)
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(log_table)

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
    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
                value_transforms={
                    "text": [helpers.pre_tag],
                    "job": [helpers.render_job_run_link],
                    "button_class": [helpers.render_button_class],
                },
            ),
        )
    )


#
# Change logging
#
class ObjectChangeUIViewSet(ObjectDetailViewMixin, ObjectListViewMixin):
    filterset_class = filters.ObjectChangeFilterSet
    filterset_form_class = forms.ObjectChangeFilterForm
    queryset = ObjectChange.objects.all()
    serializer_class = serializers.ObjectChangeSerializer
    table_class = tables.ObjectChangeTable
    action_buttons = ("export",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_detail_content = object_detail.ObjectDetailContent()
        # Remove "Advanced" tab while keeping the main.
        self.object_detail_content.tabs = self.object_detail_content.tabs[:1]

    # 2.0 TODO: Remove this remapping and solve it at the `BaseFilterSet` as it is addressing a breaking change.
    def get(self, request, *args, **kwargs):
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

        return super().get(request=request, *args, **kwargs)

    def get_extra_context(self, request, instance):
        """
        Adds snapshot diff and related changes table for the object change detail view.
        """
        context = super().get_extra_context(request, instance)

        if self.action == "retrieve":
            related_changes = instance.get_related_changes(user=request.user).filter(request_id=instance.request_id)
            related_changes_table = tables.ObjectChangeTable(
                data=related_changes[:50],  # Limit for performance
                orderable=False,
            )
            snapshots = instance.get_snapshots()

            context.update(
                {
                    "diff_added": snapshots["differences"]["added"],
                    "diff_removed": snapshots["differences"]["removed"],
                    "next_change": instance.get_next_change(request.user),
                    "prev_change": instance.get_prev_change(request.user),
                    "related_changes_table": related_changes_table,
                    "related_changes_count": related_changes.count(),
                }
            )

        return context


class ObjectChangeLogView(generic.GenericView):
    """
    Present a history of changes made to a particular object.

    base_template: Specify to explicitly identify the base object detail template to render.
        If not provided, "<app>/<model>.html", "<app>/<model>_retrieve.html", or "generic/object_retrieve.html"
        will be used, as per `get_base_template()`.
    """

    base_template: Optional[str] = None

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

        base_template = get_base_template(self.base_template, model)

        return render(
            request,
            "generic/object_changelog.html",
            {
                "object": obj,
                "verbose_name": obj._meta.verbose_name,
                "verbose_name_plural": obj._meta.verbose_name_plural,
                "table": objectchanges_table,
                "base_template": base_template,
                "active_tab": "changelog",
                "breadcrumbs": self.get_breadcrumbs(obj, view_type=""),
                "view_titles": self.get_view_titles(obj, view_type=""),
                "detail": True,
                "view_action": "changelog",
            },
        )


#
# Metadata
#


class MetadataTypeUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.MetadataTypeBulkEditForm
    filterset_class = filters.MetadataTypeFilterSet
    filterset_form_class = forms.MetadataTypeFilterForm
    form_class = forms.MetadataTypeForm
    queryset = MetadataType.objects.all()
    serializer_class = serializers.MetadataTypeSerializer
    table_class = tables.MetadataTypeTable

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                exclude_fields=("content_types",),
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.LEFT_HALF,
                weight=200,
                context_table_key="choices",
                table_title="Choices",
            ),
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                fields=["content_types"],
                label="Assignment",
            ),
        ),
    )

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        if self.action in ("create", "update"):
            if request.POST:
                context["choices"] = forms.MetadataChoiceFormSet(data=request.POST, instance=instance)
            else:
                context["choices"] = forms.MetadataChoiceFormSet(instance=instance)
        elif self.action == "retrieve":
            context["choices"] = tables.MetadataChoiceTable(instance.choices.all())

        return context

    def form_save(self, form, **kwargs):
        obj = super().form_save(form, **kwargs)

        # Process the formset for choices
        ctx = self.get_extra_context(self.request, obj)
        choices = ctx["choices"]
        if choices.is_valid():
            choices.save()
        else:
            raise ValidationError(choices.errors)

        return obj


class ObjectMetadataUIViewSet(
    ObjectListViewMixin,
):
    filterset_class = filters.ObjectMetadataFilterSet
    filterset_form_class = forms.ObjectMetadataFilterForm
    queryset = ObjectMetadata.objects.all().order_by("assigned_object_type", "assigned_object_id", "scoped_fields")
    serializer_class = serializers.ObjectMetadataSerializer
    table_class = tables.ObjectMetadataTable
    action_buttons = ("export",)


#
# Notes
#


class NoteUIViewSet(
    ObjectDestroyViewMixin,
    ObjectDetailViewMixin,
    ObjectEditViewMixin,
    ObjectListViewMixin,
    ObjectChangeLogViewMixin,
    ObjectDataComplianceViewMixin,
):
    filterset_class = filters.NoteFilterSet
    filterset_form_class = forms.NoteFilterForm
    form_class = forms.NoteForm
    queryset = Note.objects.all()
    serializer_class = serializers.NoteSerializer
    table_class = tables.NoteTable
    action_buttons = ()
    breadcrumbs = Breadcrumbs(
        items={
            "detail": [
                ModelBreadcrumbItem(model=Note),
                ModelBreadcrumbItem(
                    model=lambda c: c["object"].assigned_object,
                    action="notes",
                    reverse_kwargs=lambda c: {"pk": c["object"].assigned_object.pk},
                    label=lambda c: c["object"].assigned_object,
                    should_render=lambda c: c["object"].assigned_object,
                ),
            ]
        }
    )

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=["user", "assigned_object_type", "assigned_object"],
            ),
            object_detail.ObjectTextPanel(
                label="Text",
                section=SectionChoices.LEFT_HALF,
                weight=200,
                object_field="note",
                render_as=object_detail.ObjectTextPanel.RenderOptions.MARKDOWN,
            ),
        ),
    )

    def form_save(self, form, commit=True, *args, **kwargs):
        """
        Save the form instance while ensuring the Note's `user` and `user_name` fields
        are correctly populated.

        Args:
            form (Form): The validated form instance to be saved.
            commit (bool): If True, save the instance to the database immediately.
            *args, **kwargs: Additional arguments to maintain compatibility with
                            the parent method signature.

        Returns:
            Note: The saved or unsaved Note instance with `user` and `user_name` set.

        Behavior:
            - Sets `user` to the currently authenticated user.
            - Sets `user_name` to the username of the authenticated user.
            - Saves the instance if `commit=True`.
        """
        # Get instance without committing to DB
        obj = super().form_save(form, commit=False, *args, **kwargs)

        # Assign user info (only authenticated users can create notes)
        obj.user = self.request.user
        obj.user_name = self.request.user.get_username()

        # Save to DB if commit is True
        if commit:
            obj.save()

        return obj


class ObjectNotesView(generic.GenericView):
    """
    Present a list of notes associated to a particular object.

    base_template: Specify to explicitly identify the base object detail template to render.
        If not provided, "<app>/<model>.html", "<app>/<model>_retrieve.html", or "generic/object_retrieve.html"
        will be used, as per `get_base_template()`.
    """

    base_template: Optional[str] = None

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
        notes_table = tables.NoteTable(obj.notes.restrict(request.user, "view"))

        # Apply the request context
        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(notes_table)

        base_template = get_base_template(self.base_template, model)

        return render(
            request,
            "generic/object_notes.html",
            {
                "object": obj,
                "verbose_name": obj._meta.verbose_name,
                "verbose_name_plural": obj._meta.verbose_name_plural,
                "table": notes_table,
                "base_template": base_template,
                "active_tab": "notes",
                "form": notes_form,
                "breadcrumbs": self.get_breadcrumbs(obj, view_type=""),
                "view_titles": self.get_view_titles(obj, view_type=""),
                "detail": True,
                "view_action": "notes",
            },
        )


#
# Relationship
#


class RelationshipUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.RelationshipBulkEditForm
    filterset_class = filters.RelationshipFilterSet
    filterset_form_class = forms.RelationshipFilterForm
    form_class = forms.RelationshipForm
    serializer_class = serializers.RelationshipSerializer
    table_class = tables.RelationshipTable
    queryset = Relationship.objects.all()

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                label="Relationship",
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
                exclude_fields=[
                    "source_type",
                    "source_label",
                    "source_hidden",
                    "source_filter",
                    "destination_type",
                    "destination_label",
                    "destination_hidden",
                    "destination_filter",
                ],
            ),
            object_detail.ObjectFieldsPanel(
                label="Source Attributes",
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                fields=["source_type", "source_label", "source_hidden", "source_filter"],
            ),
            object_detail.ObjectFieldsPanel(
                label="Destination Attributes",
                section=SectionChoices.RIGHT_HALF,
                weight=200,
                fields=["destination_type", "destination_label", "destination_hidden", "destination_filter"],
            ),
        )
    )


class RelationshipAssociationUIViewSet(ObjectListViewMixin, ObjectDestroyViewMixin, ObjectBulkDestroyViewMixin):
    filterset_class = filters.RelationshipAssociationFilterSet
    filterset_form_class = forms.RelationshipAssociationFilterForm
    serializer_class = serializers.RelationshipAssociationSerializer
    table_class = tables.RelationshipAssociationTable
    queryset = RelationshipAssociation.objects.all()
    action_buttons = ()


#
# Roles
#


class RoleUIViewSet(viewsets.NautobotUIViewSet):
    """`Roles` UIViewSet."""

    queryset = Role.objects.all()
    bulk_update_form_class = forms.RoleBulkEditForm
    filterset_class = filters.RoleFilterSet
    filterset_form_class = forms.RoleFilterForm
    form_class = forms.RoleForm
    serializer_class = serializers.RoleSerializer
    table_class = tables.RoleTable

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            context["content_types"] = instance.content_types.order_by("app_label", "model")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }

            if ContentType.objects.get_for_model(Device) in context["content_types"]:
                devices = instance.devices.restrict(request.user, "view")
                device_table = DeviceTable(devices)
                device_table.columns.hide("role")
                RequestConfig(request, paginate).configure(device_table)
                context["device_table"] = device_table

            if ContentType.objects.get_for_model(Interface) in context["content_types"]:
                interfaces = instance.interfaces.restrict(request.user, "view")
                interface_table = InterfaceTable(interfaces)
                interface_table.columns.hide("role")
                RequestConfig(request, paginate).configure(interface_table)
                context["interface_table"] = interface_table

            if ContentType.objects.get_for_model(Controller) in context["content_types"]:
                controllers = instance.controllers.restrict(request.user, "view")
                controller_table = ControllerTable(controllers)
                controller_table.columns.hide("role")
                RequestConfig(request, paginate).configure(controller_table)
                context["controller_table"] = controller_table

            if ContentType.objects.get_for_model(IPAddress) in context["content_types"]:
                ipaddress = instance.ip_addresses.restrict(request.user, "view").annotate(
                    interface_count=count_related(Interface, "ip_addresses"),
                    interface_parent_count=count_related(Device, "interfaces__ip_addresses", distinct=True),
                    vm_interface_count=count_related(VMInterface, "ip_addresses"),
                    vm_interface_parent_count=count_related(VirtualMachine, "interfaces__ip_addresses", distinct=True),
                )
                ipaddress_table = IPAddressTable(ipaddress)
                ipaddress_table.columns.hide("role")
                RequestConfig(request, paginate).configure(ipaddress_table)
                context["ipaddress_table"] = ipaddress_table

            if ContentType.objects.get_for_model(Prefix) in context["content_types"]:
                prefixes = instance.prefixes.restrict(request.user, "view")
                prefix_table = PrefixTable(prefixes, hide_hierarchy_ui=True)
                prefix_table.columns.hide("role")
                RequestConfig(request, paginate).configure(prefix_table)
                context["prefix_table"] = prefix_table
            if ContentType.objects.get_for_model(Rack) in context["content_types"]:
                racks = instance.racks.restrict(request.user, "view")
                rack_table = RackTable(racks)
                rack_table.columns.hide("role")
                RequestConfig(request, paginate).configure(rack_table)
                context["rack_table"] = rack_table
            if ContentType.objects.get_for_model(VirtualMachine) in context["content_types"]:
                virtual_machines = instance.virtual_machines.restrict(request.user, "view")
                virtual_machine_table = VirtualMachineTable(virtual_machines)
                virtual_machine_table.columns.hide("role")
                RequestConfig(request, paginate).configure(virtual_machine_table)
                context["virtual_machine_table"] = virtual_machine_table
            if ContentType.objects.get_for_model(VMInterface) in context["content_types"]:
                vm_interfaces = instance.vm_interfaces.restrict(request.user, "view")
                vminterface_table = VMInterfaceTable(vm_interfaces)
                vminterface_table.columns.hide("role")
                RequestConfig(request, paginate).configure(vminterface_table)
                context["vminterface_table"] = vminterface_table
            if ContentType.objects.get_for_model(VLAN) in context["content_types"]:
                vlans = instance.vlans.restrict(request.user, "view")
                vlan_table = VLANTable(vlans)
                vlan_table.columns.hide("role")
                RequestConfig(request, paginate).configure(vlan_table)
                context["vlan_table"] = vlan_table
            if ContentType.objects.get_for_model(Module) in context["content_types"]:
                modules = instance.modules.restrict(request.user, "view")
                module_table = ModuleTable(modules)
                module_table.columns.hide("role")
                RequestConfig(request, paginate).configure(module_table)
                context["module_table"] = module_table
            if ContentType.objects.get_for_model(VirtualDeviceContext) in context["content_types"]:
                vdcs = instance.virtual_device_contexts.restrict(request.user, "view")
                vdc_table = VirtualDeviceContextTable(vdcs)
                vdc_table.columns.hide("role")
                RequestConfig(request, paginate).configure(vdc_table)
                context["vdc_table"] = vdc_table
            if ContentType.objects.get_for_model(VPN) in context["content_types"]:
                vpns = instance.vpns.restrict(request.user, "view")
                vpn_table = VPNTable(vpns)
                vpn_table.columns.hide("role")
                RequestConfig(request, paginate).configure(vpn_table)
                context["vpn_table"] = vpn_table
            if ContentType.objects.get_for_model(VPNProfile) in context["content_types"]:
                vpn_profiles = instance.vpn_profiles.restrict(request.user, "view")
                vpn_profile_table = VPNProfileTable(vpn_profiles)
                vpn_profile_table.columns.hide("role")
                RequestConfig(request, paginate).configure(vpn_profile_table)
                context["vpn_profile_table"] = vpn_profile_table
            if ContentType.objects.get_for_model(VPNTunnel) in context["content_types"]:
                vpn_tunnels = instance.vpn_tunnels.restrict(request.user, "view")
                vpn_tunnel_table = VPNTunnelTable(vpn_tunnels)
                vpn_tunnel_table.columns.hide("role")
                RequestConfig(request, paginate).configure(vpn_tunnel_table)
                context["vpn_tunnel_table"] = vpn_tunnel_table
            if ContentType.objects.get_for_model(VPNTunnelEndpoint) in context["content_types"]:
                vpn_tunnel_endpoints = instance.vpn_tunnel_endpoints.restrict(request.user, "view")
                vpn_tunnel_endpoint_table = VPNTunnelEndpointTable(vpn_tunnel_endpoints)
                vpn_tunnel_endpoint_table.columns.hide("role")
                RequestConfig(request, paginate).configure(vpn_tunnel_endpoint_table)
                context["vpn_tunnel_endpoint_table"] = vpn_tunnel_endpoint_table
        return context


#
# Secrets
#


class SecretUIViewSet(
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectEditViewMixin,
    ObjectDestroyViewMixin,
    ObjectBulkCreateViewMixin,  # 3.0 TODO: remove, unused
    ObjectBulkDestroyViewMixin,
    # no ObjectBulkUpdateViewMixin here yet
    ObjectChangeLogViewMixin,
    ObjectDataComplianceViewMixin,
    ObjectNotesViewMixin,
):
    queryset = Secret.objects.all()
    form_class = forms.SecretForm
    filterset_class = filters.SecretFilterSet
    filterset_form_class = forms.SecretFilterForm
    table_class = tables.SecretTable

    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            object_detail.ObjectFieldsPanel(
                weight=100, section=SectionChoices.LEFT_HALF, fields="__all__", exclude_fields=["parameters"]
            ),
            object_detail.KeyValueTablePanel(
                weight=200, section=SectionChoices.LEFT_HALF, label="Parameters", context_data_key="parameters"
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                table_title="Groups containing this secret",
                table_class=tables.SecretsGroupTable,
                table_attribute="secrets_groups",
                distinct=True,
                related_field_name="secrets",
                footer_content_template_path=None,
            ),
        ],
        extra_buttons=[
            object_detail.Button(
                weight=100,
                label="Check Secret",
                icon="mdi-test-tube",
                javascript_template_path="extras/secret_check.js",
                attributes={"onClick": "checkSecret()"},
            ),
        ],
    )

    def get_extra_context(self, request, instance):
        ctx = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            ctx["parameters"] = instance.parameters
        return ctx


class SecretProviderParametersFormView(generic.GenericView):
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


class SecretsGroupUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.SecretsGroupBulkEditForm
    filterset_class = filters.SecretsGroupFilterSet
    filterset_form_class = forms.SecretsGroupFilterForm
    form_class = forms.SecretsGroupForm
    serializer_class = serializers.SecretsGroupSerializer
    table_class = tables.SecretsGroupTable
    queryset = SecretsGroup.objects.all()

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                label="Secrets Group Details",
                fields=["description"],
                section=SectionChoices.LEFT_HALF,
                weight=100,
            ),
            object_detail.ObjectsTablePanel(
                table_class=tables.SecretsGroupAssociationTable,
                table_filter="secrets_group",
                related_field_name="secrets_groups",
                related_list_url_name="extras:secret_list",
                table_title="Secrets",
                section=SectionChoices.LEFT_HALF,
                weight=200,
            ),
        )
    )

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        if self.action in ("create", "update"):
            if request.method == "POST":
                context["secrets"] = forms.SecretsGroupAssociationFormSet(data=request.POST, instance=instance)
            else:
                context["secrets"] = forms.SecretsGroupAssociationFormSet(instance=instance)
        return context

    def form_save(self, form, **kwargs):
        obj = super().form_save(form, **kwargs)
        secrets = forms.SecretsGroupAssociationFormSet(data=self.request.POST, instance=form.instance)

        if secrets.is_valid():
            secrets.save()
        else:
            raise ValidationError(secrets.errors)

        return obj


#
# Static Groups
#


class StaticGroupAssociationUIViewSet(
    ObjectBulkDestroyViewMixin,
    ObjectChangeLogViewMixin,
    ObjectDestroyViewMixin,
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    # TODO anything else?
):
    filterset_class = filters.StaticGroupAssociationFilterSet
    filterset_form_class = forms.StaticGroupAssociationFilterForm
    queryset = StaticGroupAssociation.all_objects.all()
    serializer_class = serializers.StaticGroupAssociationSerializer
    table_class = tables.StaticGroupAssociationTable
    action_buttons = ("export",)

    def alter_queryset(self, request):
        queryset = super().alter_queryset(request)
        # Default to only showing associations for static-type groups:
        if request is None or "dynamic_group" not in request.GET:
            queryset = queryset.filter(dynamic_group__group_type=DynamicGroupTypeChoices.TYPE_STATIC)
        return queryset


#
# Custom statuses
#


class StatusUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.StatusBulkEditForm
    filterset_class = filters.StatusFilterSet
    filterset_form_class = forms.StatusFilterForm
    form_class = forms.StatusForm
    serializer_class = serializers.StatusSerializer
    table_class = tables.StatusTable
    queryset = Status.objects.all()

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(object_detail.ObjectFieldsPanel(weight=100, section=SectionChoices.LEFT_HALF, fields="__all__"),)
    )


#
# Tags
#


class TagUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.TagBulkEditForm
    filterset_class = filters.TagFilterSet
    filterset_form_class = forms.TagFilterForm
    form_class = forms.TagForm
    queryset = Tag.objects.all()
    serializer_class = serializers.TagSerializer
    table_class = tables.TagTable

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                table_class=tables.TaggedItemTable,
                table_title="Tagged Objects",
                table_filter="tag",
                select_related_fields=["content_type"],
                prefetch_related_fields=["content_object"],
                include_paginator=True,
                enable_related_link=False,
            ),
        ),
    )

    def alter_queryset(self, request):
        queryset = super().alter_queryset(request)

        # Only annotate for list, bulk_edit, bulk_delete views
        if self.action in ["list", "bulk_update", "bulk_destroy"]:
            queryset = queryset.annotate(items=count_related(TaggedItem, "tag"))

        return queryset


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

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
                value_transforms={
                    "address": [helpers.render_address],
                    "email": [helpers.hyperlinked_email],
                    "phone": [helpers.hyperlinked_phone_number],
                },
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                table_class=tables.ContactTable,
                table_filter="teams",
                table_title="Assigned Contacts",
                exclude_columns=["actions"],
                add_button_route=None,
            ),
            object_detail.ObjectsTablePanel(
                weight=200,
                section=SectionChoices.FULL_WIDTH,
                table_class=tables.ContactAssociationTable,
                table_filter="team",
                table_title="Contact For",
                add_button_route=None,
                enable_related_link=False,
            ),
        )
    )


#
# Webhooks
#


class WebhookUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.WebhookBulkEditForm
    filterset_class = filters.WebhookFilterSet
    filterset_form_class = forms.WebhookFilterForm
    form_class = forms.WebhookForm
    queryset = Webhook.objects.all()
    serializer_class = serializers.WebhookSerializer
    table_class = tables.WebhookTable

    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            object_detail.ObjectFieldsPanel(
                label="Webhook",
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=("name", "content_types", "type_create", "type_update", "type_delete", "enabled"),
            ),
            object_detail.ObjectFieldsPanel(
                label="HTTP",
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=("http_method", "http_content_type", "payload_url", "additional_headers"),
                value_transforms={"additional_headers": [partial(helpers.pre_tag, format_empty_value=False)]},
            ),
            object_detail.ObjectFieldsPanel(
                label="Security",
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=("secret", "ssl_verification", "ca_file_path"),
            ),
            object_detail.ObjectTextPanel(
                label="Body Template",
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                object_field="body_template",
                render_as=object_detail.BaseTextPanel.RenderOptions.CODE,
            ),
        ]
    )


#
# Job Extra Views
#
# NOTE: Due to inheritance, JobObjectChangeLogView and JobObjectNotesView can only be
# constructed below # ObjectChangeLogView and ObjectNotesView.


class JobObjectChangeLogView(ObjectChangeLogView):
    base_template = "generic/object_retrieve.html"


class JobObjectNotesView(ObjectNotesView):
    base_template = "generic/object_retrieve.html"
