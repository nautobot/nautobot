from datetime import date

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
    weight = models.PositiveIntegerField(
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
        unique_together = [["approval_workflow", "name"], ["approval_workflow", "weight"]]
        ordering = ["approval_workflow", "weight"]

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

    @property
    def current_stage(self):
        """
        Return the current stage of the workflow.
        1. Return the stage that is denied if there is a stage that has been denied.
        2. Return the first stage that is pending, if there is no stage that has been approved or denied.
        3. Return the stage that is pending that is immediately after the last stage that has been approved.
        4. Return None, if all stages are approved.
        """
        # Check if there is a stage that is denied
        denied_stage = self.approval_workflow_stage_instances.filter(state=ApprovalWorkflowStateChoices.DENIED)
        if denied_stage.exists():
            return denied_stage.first()
        # Get the pending stage with the lowest weight
        pending_stages = self.approval_workflow_stage_instances.filter(
            state=ApprovalWorkflowStateChoices.PENDING
        ).order_by("approval_workflow_stage__weight")
        if pending_stages.exists():
            return pending_stages.first()

        # No pending or denied stages at this point, so return None because all stages are approved
        return None

    def save(self, *args, **kwargs):
        """
        Override the save() method to
        1. Update its status to denied, if one of the approval workflow stage instances is denied.
        2. Update its status to approved, if all of the approval workflow stage instances are approved.
        Args:
            *args: positional arguments
            **kwargs: keyword arguments
        """
        # Check if there is one or more denied response for this stage instance
        denied_stages = self.approval_workflow_stage_instances.filter(state=ApprovalWorkflowStateChoices.DENIED)
        if denied_stages.exists():
            self.current_state = ApprovalWorkflowStateChoices.DENIED
        # Check if all stages are approved
        approved_stages = self.approval_workflow_stage_instances.filter(state=ApprovalWorkflowStateChoices.APPROVED)
        if approved_stages.count() == self.approval_workflow.approval_workflow_stages.count():
            self.current_state = ApprovalWorkflowStateChoices.APPROVED
        super().save(*args, **kwargs)


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

    def save(self, *args, **kwargs):
        """
        Override save method:
        1. set the stage as denied if one user denies it.
        2. set the stage as approved if min number of eligibl users approve it.
        3. set decision_date when state is changed to APPROVED or DENIED.
        4. call save() on the parent ApprovalWorkflowInstance to potentially update its state as well.

        Args:
            *args: positional arguments
            **kwargs: keyword arguments
        """
        # Check if there is one or more denied response for this stage instance
        denied_responses = self.approval_workflow_stage_instance_responses.filter(
            state=ApprovalWorkflowStateChoices.DENIED
        )
        if denied_responses.exists():
            self.state = ApprovalWorkflowStateChoices.DENIED

        # Check if the number of approvers is met
        approved_responses = self.approval_workflow_stage_instance_responses.filter(
            state=ApprovalWorkflowStateChoices.APPROVED
        )
        if approved_responses.count() >= self.approval_workflow_stage.min_approvers:
            self.state = ApprovalWorkflowStateChoices.APPROVED

        # Set the decision date if the state is changed to APPROVED or DENIED
        decision_made = self.state in [ApprovalWorkflowStateChoices.APPROVED, ApprovalWorkflowStateChoices.DENIED]
        if decision_made:
            self.decision_date = date.today()
        super().save(*args, **kwargs)
        if decision_made:
            self.approval_workflow_instance.save()


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

    def save(self, *args, **kwargs):
        """
        Override the save method to call save() on the parent ApprovalWorkflowStageInstance as well.
        Args:
            *args: positional arguments
            **kwargs: keyword arguments
        """
        super().save(*args, **kwargs)
        # Call save() on the parent ApprovalWorkflowStageInstance to potentially update its state as well
        if self.state in [
            ApprovalWorkflowStateChoices.APPROVED,
            ApprovalWorkflowStateChoices.DENIED,
        ]:
            self.approval_workflow_stage_instance.save()
