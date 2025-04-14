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
    def active_stage(self):
        """
        Return the current stage of the workflow. The current stage is the first stage that is not yet approved.
        If all stages are approved, return None.
        Returns:
            ApprovalWorkflowStageInstance: The current stage of the workflow.
        """
        first_nonapproved_stage = self.approval_workflow_stage_instances.filter(
            state__n=ApprovalWorkflowStateChoices.APPROVED
        ).first()
        return first_nonapproved_stage

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
        1. Set the stage as denied if one user denies it.
        2. Set the stage as approved if min number of eligible users approve it.
        3. Set decision_date when state is changed to APPROVED or DENIED if the state was just set to one of the terminal values.
        4. Update the parent ApprovalWorkFlow instance status to denied, if the stage is denied.
        2. Update the parent ApprovalWorkFlow instance status to approved, if all of the approval workflow stage instances are approved.

        Args:
            *args: positional arguments
            **kwargs: keyword arguments
        """
        # store previous state in case it is changed
        previous_state = self.state
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
        decision_made = (
            self.state in [ApprovalWorkflowStateChoices.APPROVED, ApprovalWorkflowStateChoices.DENIED]
            and previous_state != self.state
        )
        if decision_made:
            self.decision_date = date.today()
        super().save(*args, **kwargs)

        # Modify the parent ApprovalWorkflowInstance to potentially update its state as well
        # If this stage is approved or denied.
        if decision_made:
            approval_workflow_instance = self.approval_workflow_instance
            # Check if there is one or more denied response for this stage instance
            denied_stages = approval_workflow_instance.approval_workflow_stage_instances.filter(
                state=ApprovalWorkflowStateChoices.DENIED
            )
            if denied_stages.exists():
                approval_workflow_instance.current_state = ApprovalWorkflowStateChoices.DENIED
            # Check if all stages are approved
            approved_stages = approval_workflow_instance.filter(state=ApprovalWorkflowStateChoices.APPROVED)
            if approved_stages.count() == self.approval_workflow.approval_workflow_stages.count():
                approval_workflow_instance.current_state = ApprovalWorkflowStateChoices.APPROVED
            approval_workflow_instance.save()


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
        previous_state = self.state
        super().save(*args, **kwargs)
        # Call save() on the parent ApprovalWorkflowStageInstance to potentially update its state as well
        # If this stage is approved or denied and the state has just been updated.
        if (
            self.state
            in [
                ApprovalWorkflowStateChoices.APPROVED,
                ApprovalWorkflowStateChoices.DENIED,
            ]
            and previous_state != self.state
        ):
            self.approval_workflow_stage_instance.save()
