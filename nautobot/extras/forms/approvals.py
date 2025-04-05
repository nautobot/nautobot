"""Forms for Approval Workflow"""

from django import forms
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType

from nautobot.core.forms import (
    add_blank_choice,
    DynamicModelChoiceField,
    JSONField,
    StaticSelect2,
)
from nautobot.extras.choices import ApprovalWorkflowStateChoices
from nautobot.extras.constants import APPROVAL_WORKFLOW_MODELS
from nautobot.extras.forms import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm
from nautobot.extras.models import (
    ApprovalWorkflow,
    ApprovalWorkflowInstance,
    ApprovalWorkflowStage,
    ApprovalWorkflowStageInstance,
    ApprovalWorkflowStageInstanceResponse,
)


class ApprovalWorkflowForm(NautobotModelForm):
    """Form for creating and updating ApprovalWorkflow."""

    model_content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(APPROVAL_WORKFLOW_MODELS).order_by("app_label", "model"),
        required=True,
        label="Model Content Type",
    )
    model_constraints = JSONField(required=False, label="Model Constraints")

    class Meta:
        """Meta attributes."""

        model = ApprovalWorkflow
        fields = "__all__"


class ApprovalWorkflowBulkEditForm(NautobotBulkEditForm):
    """ApprovalWorkflow bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=ApprovalWorkflow.objects.all(), widget=forms.MultipleHiddenInput)

    class Meta:
        """Meta attributes."""

        model = ApprovalWorkflow
        nullable_fields = ["model_constraints"]


class ApprovalWorkflowFilterForm(NautobotFilterForm):
    """Filter form for ApprovalWorkflow."""

    model = ApprovalWorkflow
    q = forms.CharField(required=False, label="Search")


class ApprovalWorkflowStageForm(NautobotModelForm):
    """Form for creating and updating ApprovalWorkflowStage."""

    approval_workflow = DynamicModelChoiceField(
        queryset=ApprovalWorkflow.objects.all(),
        required=True,
        label="Approval Workflow",
    )
    approver_group = DynamicModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        label="Approver Group",
        help_text="User group that can approve this stage.",
    )

    class Meta:
        """Meta attributes."""

        model = ApprovalWorkflowStage
        fields = "__all__"


class ApprovalWorkflowStageBulkEditForm(NautobotBulkEditForm):
    """ApprovalWorkflowStage bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=ApprovalWorkflowStage.objects.all(), widget=forms.MultipleHiddenInput)
    sequence_weight = forms.IntegerField(required=False, label="Sequence Weight")
    min_approvers = forms.IntegerField(required=False, label="Min Approvers")
    denial_message = forms.CharField(required=False, label="Denial Message")

    class Meta:
        """Meta attributes."""

        model = ApprovalWorkflowStage
        nullable_fields = ["denial_message"]


class ApprovalWorkflowStageFilterForm(NautobotFilterForm):
    """Filter form for ApprovalWorkflowStage."""

    model = ApprovalWorkflowStage
    q = forms.CharField(required=False, label="Search")


class ApprovalWorkflowInstanceForm(NautobotModelForm):
    """Form for creating and updating ApprovalWorkflowInstance."""

    approval_workflow = DynamicModelChoiceField(
        queryset=ApprovalWorkflow.objects.all(),
        required=True,
        label="Approval Workflow",
    )
    object_under_review_content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(APPROVAL_WORKFLOW_MODELS).order_by("app_label", "model"),
        required=True,
        label="Object Under Review Content Type",
    )

    class Meta:
        """Meta attributes."""

        model = ApprovalWorkflowInstance
        fields = "__all__"


class ApprovalWorkflowInstanceBulkEditForm(NautobotBulkEditForm):
    """ApprovalWorkflowInstance bulk edit form."""

    pk = forms.ModelMultipleChoiceField(
        queryset=ApprovalWorkflowInstance.objects.all(), widget=forms.MultipleHiddenInput
    )
    current_state = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(ApprovalWorkflowStateChoices),
        widget=StaticSelect2,
        label="Current State",
    )

    class Meta:
        """Meta attributes."""

        model = ApprovalWorkflowInstance
        nullable_fields = [
            # TODO INIT Add any fields that should be nullable
            "approval_workflow",
            "object_under_review_content_type",
            "object_under_review_object_id",
            "current_state",
        ]


class ApprovalWorkflowInstanceFilterForm(NautobotFilterForm):
    """Filter form for ApprovalWorkflowInstance."""

    model = ApprovalWorkflowInstance
    q = forms.CharField(required=False, label="Search")


class ApprovalWorkflowStageInstanceForm(NautobotModelForm):
    """Form for creating and updating ApprovalWorkflowStageInstance."""

    approval_workflow_instance = DynamicModelChoiceField(
        queryset=ApprovalWorkflowInstance.objects.all(),
        required=True,
        label="Approval Workflow Instance",
    )
    approval_workflow_stage = DynamicModelChoiceField(
        queryset=ApprovalWorkflowStage.objects.all(),
        required=True,
        label="Approval Workflow Stage",
        query_params={"approval_workflow_instance": "$approval_workflow_instance"},
    )

    class Meta:
        """Meta attributes."""

        model = ApprovalWorkflowStageInstance
        fields = "__all__"


class ApprovalWorkflowStageInstanceBulkEditForm(NautobotBulkEditForm):
    """ApprovalWorkflowStageInstance bulk edit form."""

    pk = forms.ModelMultipleChoiceField(
        queryset=ApprovalWorkflowStageInstance.objects.all(), widget=forms.MultipleHiddenInput
    )
    state = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(ApprovalWorkflowStateChoices),
        widget=StaticSelect2,
        label="State",
    )
    decision_date = forms.DateField(required=False, label="Decision Date")

    class Meta:
        """Meta attributes."""

        model = ApprovalWorkflowStageInstance
        nullable_fields = [
            # TODO INIT Add any fields that should be nullable
            "approval_workflow_instance",
            "approval_workflow_stage",
            "state",
            "decision_date",
        ]


class ApprovalWorkflowStageInstanceFilterForm(NautobotFilterForm):
    """Filter form for ApprovalWorkflowStageInstance."""

    model = ApprovalWorkflowStageInstance
    q = forms.CharField(required=False, label="Search")


class ApprovalWorkflowStageInstanceResponseForm(NautobotModelForm):
    """Form for creating and updating ApprovalWorkflowStageInstanceResponse."""

    class Meta:
        """Meta attributes."""

        model = ApprovalWorkflowStageInstanceResponse
        fields = "__all__"


class ApprovalWorkflowStageInstanceResponseBulkEditForm(NautobotBulkEditForm):
    """ApprovalWorkflowStageInstanceResponse bulk edit form."""

    pk = forms.ModelMultipleChoiceField(
        queryset=ApprovalWorkflowStageInstanceResponse.objects.all(), widget=forms.MultipleHiddenInput
    )
    comments = forms.CharField(required=False, label="Comments")
    state = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(ApprovalWorkflowStateChoices),
        widget=StaticSelect2,
        label="State",
    )

    class Meta:
        """Meta attributes."""

        model = ApprovalWorkflowStageInstanceResponse
        nullable_fields = [
            # TODO INIT Add any fields that should be nullable
            "approval_workflow_stage_instance",
            "user",
            "comments",
            "state",
        ]


class ApprovalWorkflowStageInstanceResponseFilterForm(NautobotFilterForm):
    """Filter form for ApprovalWorkflowStageInstanceResponse."""

    model = ApprovalWorkflowStageInstanceResponse
    q = forms.CharField(required=False, label="Search")
