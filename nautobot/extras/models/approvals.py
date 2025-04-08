from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseModel
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.choices import ApprovalWorkflowStateChoices
from nautobot.extras.constants import APPROVAL_WORKFLOW_MODELS
from nautobot.extras.utils import extras_features
from nautobot.users.models import User


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class ApprovalWorkflow(PrimaryModel):
    """ApprovalWorkflow model."""

    name = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        unique=True,
    )
    model_content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name="+",
        limit_choices_to=APPROVAL_WORKFLOW_MODELS,
    )
    model_constraints = models.JSONField(
        blank=True,
        default=dict,
        help_text="Constraints to filter the objects that can be approved using this workflow.",
    )

    class Meta:
        """Meta class for ApprovalWorkflow."""

        verbose_name = "Approval Workflow"

    def __str__(self):
        """Stringify instance."""
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ApprovalWorkflowStage(PrimaryModel):
    """ApprovalWorkflowStage model."""

    approval_workflow = models.ForeignKey(
        to="extras.ApprovalWorkflow",
        related_name="approval_workflow_stages",
        verbose_name="Approval Workflow",
        on_delete=models.PROTECT,
        help_text="Approval workflow to which this stage belongs.",
    )
    sequence_weight = models.PositiveIntegerField(
        help_text="The weight dictates the order in which this stage will need to be approved. The lower the number, the earlier it will be.",
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    min_approvers = models.PositiveIntegerField(
        help_text="Number of minimum approvers required to approve this stage.",
    )
    denial_message = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Message to show when the stage is denied."
    )
    approver_group = models.ForeignKey(
        to=Group,
        related_name="approval_workflow_stages",
        verbose_name="Group",
        help_text="Group of users who are eligible to approve this stage.",
        on_delete=models.PROTECT,
    )

    class Meta:
        """Meta class for ApprovalWorkflowStage."""

        verbose_name = "Approval Workflow Stage"
        unique_together = [["approval_workflow", "name"], ["approval_workflow", "sequence_weight"]]

    def __str__(self):
        """Stringify instance."""
        return f"{self.approval_workflow}: Stage {self.name}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ApprovalWorkflowInstance(PrimaryModel):
    """ApprovalWorkflowInstance model."""

    approval_workflow = models.ForeignKey(
        to="extras.ApprovalWorkflow",
        related_name="approval_workflow_instances",
        verbose_name="Approval Workflow",
        on_delete=models.PROTECT,
        help_text="Approval workflow to which this instance belongs.",
    )
    object_under_review = GenericForeignKey(
        ct_field="object_under_review_content_type", fk_field="object_under_review_object_id"
    )
    object_under_review_content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name="+",
        limit_choices_to=APPROVAL_WORKFLOW_MODELS,
    )
    object_under_review_object_id = models.UUIDField(db_index=True)
    current_state = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=ApprovalWorkflowStateChoices,
        default=ApprovalWorkflowStateChoices.PENDING,
        help_text="Current state of the approval workflow instance. Eligible values are: Pending, Approved, Denied.",
    )

    class Meta:
        """Meta class for ApprovalWorkflowInstance."""

        verbose_name = "Approval Workflow Instance"

    def __str__(self):
        """Stringify instance."""
        return f"{self.approval_workflow.name}: {self.object_under_review} ({self.current_state})"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ApprovalWorkflowStageInstance(PrimaryModel):
    """ApprovalWorkflowStageInstance model."""

    approval_workflow_instance = models.ForeignKey(
        to="extras.ApprovalWorkflowInstance",
        related_name="approval_workflow_stage_instances",
        verbose_name="Approval Workflow Instance",
        on_delete=models.PROTECT,
        help_text="Approval workflow instance to which this stage instance belongs.",
    )
    approval_workflow_stage = models.ForeignKey(
        to="extras.ApprovalWorkflowStage",
        related_name="approval_workflow_stage_instances",
        verbose_name="Approval Workflow Stage",
        on_delete=models.PROTECT,
        help_text="Approval workflow stage to which this instance belongs.",
    )
    state = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=ApprovalWorkflowStateChoices,
        default=ApprovalWorkflowStateChoices.PENDING,
        help_text="State of the approval workflow stage instance. Eligible values are: Pending, Approved, Denied.",
    )
    decision_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date when the decision of approval/denial was made.",
    )

    class Meta:
        """Meta class for ApprovalWorkflowStageInstance."""

        verbose_name = "Approval Workflow Stage Instance"

    def __str__(self):
        """Stringify instance."""
        return f"{self.approval_workflow_stage}: {self.state}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class ApprovalWorkflowStageInstanceResponse(BaseModel):
    """ApprovalWorkflowStageInstanceResponse model."""

    approval_workflow_stage_instance = models.ForeignKey(
        to="extras.ApprovalWorkflowStageInstance",
        related_name="approval_workflow_stage_instance_responses",
        verbose_name="Approval Workflow Stage Instance",
        on_delete=models.PROTECT,
    )
    user = models.ForeignKey(
        to=User,
        related_name="approval_workflow_stage_instance_responses",
        verbose_name="User",
        on_delete=models.PROTECT,
    )
    comments = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        help_text="User comments to explain the decision that he/she made",
    )
    state = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=ApprovalWorkflowStateChoices,
        default=ApprovalWorkflowStateChoices.PENDING,
        help_text="User response to this approval workflow stage instance. Eligible values are: Pending, Approved, Denied.",
    )

    class Meta:
        """Meta class for ApprovalWorkflowStageInstanceResponse."""

        verbose_name = "Approval Workflow Stage Instance Response"

    def __str__(self):
        """Stringify instance."""
        return f"{self.approval_workflow_stage_instance}: {self.user}"
