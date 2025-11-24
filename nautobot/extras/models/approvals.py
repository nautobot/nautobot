from typing import Optional

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldError, ValidationError
from django.db import models
from django.utils import timezone

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.extras.choices import ApprovalWorkflowStateChoices
from nautobot.extras.utils import extras_features, FeatureQuery
from nautobot.users.models import User


class ApprovalWorkflowDefinitionManager(BaseManager.from_queryset(RestrictedQuerySet)):
    use_in_migrations = True

    def find_for_model(self, model_instance: models.Model) -> Optional["ApprovalWorkflowDefinition"]:
        """Find the appropriate approval workflow definition for specific content-type.

        Returns:
            ApprovalWorkflowDefinition or None: The matching workflow definition or None if none found.
        """
        content_type = ContentType.objects.get_for_model(model_instance)

        # Get all workflow definitions for this content type, ordered by weight (highest wins)
        workflow_definitions = self.get_queryset().filter(model_content_type=content_type).order_by("-weight")

        for workflow_definition in workflow_definitions:
            if not workflow_definition.model_constraints:
                return workflow_definition

            model_class = model_instance.__class__
            try:
                # Try to get the specific instance using the constraints
                # NOTE: Any valid Django ORM lookup (e.g. __in, __icontains, __gte) will technically work here,
                # since constraints are passed directly into .filter(). However, the current UI only supports
                # simple key=value style constraints and does not provide validation for advanced lookups.
                # Maybe in 3.1 replace with a FilterSet-based implementation (similar to Relationship.source_filter
                # and Relationship.destination_filter) to provide full support
                model_class.objects.filter(**workflow_definition.model_constraints).get(pk=model_instance.pk)
                return workflow_definition
            except model_class.DoesNotExist:
                continue

        return None


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class ApprovalWorkflowDefinition(PrimaryModel):
    """ApprovalWorkflowDefinition model."""

    name = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        unique=True,
    )
    model_content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name="+",
        limit_choices_to=FeatureQuery("approval_workflows"),
    )
    model_constraints = models.JSONField(
        blank=True,
        default=dict,
        help_text="Constraints to filter the objects that can be approved using this workflow.",
    )
    weight = models.IntegerField(
        default=0, help_text="Determines workflow relevance when multiple apply. Higher weight wins."
    )
    documentation_static_path = "docs/user-guide/platform-functionality/approval-workflow.html"
    is_dynamic_group_associable = False
    is_data_compliance_model = False
    objects = ApprovalWorkflowDefinitionManager()
    is_version_controlled = False

    class Meta:
        """Meta class for ApprovalWorkflow Definition."""

        verbose_name = "Approval Workflow Definition"
        ordering = ["name"]
        unique_together = [["model_content_type", "weight"]]

    def __str__(self):
        """Stringify instance."""
        return self.name

    def clean(self):
        super().clean()
        model_class = self.model_content_type.model_class()
        if model_class is None:
            raise ValidationError({"model_content_type": "Couldn't find corresponding model class. Is it installed?"})
        try:
            model_class.objects.filter(**self.model_constraints)
        except (FieldError, AttributeError) as exc:
            raise ValidationError({"model_constraints": f"Invalid query filter: {exc}"})


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ApprovalWorkflowStageDefinition(OrganizationalModel):
    """ApprovalWorkflowStageDefinition model."""

    approval_workflow_definition = models.ForeignKey(
        to="extras.ApprovalWorkflowDefinition",
        related_name="approval_workflow_stage_definitions",
        verbose_name="Approval Workflow Definition",
        on_delete=models.CASCADE,
        help_text="Approval workflow definition to which this stage belongs.",
    )
    sequence = models.PositiveIntegerField(
        help_text="The sequence dictates the order in which this stage will need to be approved. The lower the number, the earlier it will be.",
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    min_approvers = models.PositiveIntegerField(
        verbose_name="Minimum approvers",
        help_text="Minimum number of approvers required to approve this stage.",
    )
    denial_message = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Message to show when the stage is denied."
    )
    approver_group = models.ForeignKey(
        to=Group,
        related_name="approval_workflow_stage_definitions",
        verbose_name="Group",
        help_text="Group of users who are eligible to approve this stage. Only admin users can create new groups.",
        on_delete=models.PROTECT,
    )
    documentation_static_path = "docs/user-guide/platform-functionality/approval-workflow.html"
    is_version_controlled = False

    is_data_compliance_model = False

    class Meta:
        """Meta class for ApprovalWorkflowStage."""

        verbose_name = "Approval Workflow Stage Definition"
        unique_together = [["approval_workflow_definition", "name"], ["approval_workflow_definition", "sequence"]]
        ordering = ["approval_workflow_definition", "sequence"]

    def __str__(self):
        """Stringify instance."""
        return f"{self.approval_workflow_definition}: Stage {self.name}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ApprovalWorkflow(OrganizationalModel):
    """ApprovalWorkflow model."""

    approval_workflow_definition = models.ForeignKey(
        to="extras.ApprovalWorkflowDefinition",
        related_name="approval_workflows",
        verbose_name="Approval Workflow Definition",
        on_delete=models.PROTECT,
        help_text="Approval workflow definition to which this approval workflow belongs.",
    )
    object_under_review = GenericForeignKey(
        ct_field="object_under_review_content_type", fk_field="object_under_review_object_id"
    )
    object_under_review_content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name="+",
        limit_choices_to=FeatureQuery("approval_workflows"),
    )
    object_under_review_object_id = models.UUIDField(db_index=True)
    current_state = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=ApprovalWorkflowStateChoices,
        default=ApprovalWorkflowStateChoices.PENDING,
        help_text="Current state of the approval workflow. Eligible values are: Pending, Approved, Denied.",
    )
    decision_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date and time when the decision of approval/denial was made.",
    )
    # The user who triggered the approval workflow instance
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approval_workflows",
        blank=True,
        null=True,
    )
    user_name = models.CharField(max_length=150, editable=False, db_index=True)
    documentation_static_path = "docs/user-guide/platform-functionality/approval-workflow.html"

    is_data_compliance_model = False
    is_version_controlled = False

    class Meta:
        """Meta class for ApprovalWorkflow."""

        verbose_name = "Approval Workflow"
        unique_together = [
            "approval_workflow_definition",
            "object_under_review_content_type",
            "object_under_review_object_id",
        ]
        ordering = ["approval_workflow_definition"]

    def __str__(self):
        """Stringify instance."""
        return f"{self.approval_workflow_definition.name}: {self.object_under_review} ({self.current_state})"

    def get_current_state_class(self):
        return ApprovalWorkflowStateChoices.CSS_CLASSES.get(self.current_state)

    @property
    def active_stage(self):
        """
        Return the current stage of the workflow. The current stage is the first stage that is not yet approved.
        If all stages are approved, return None.
        Returns:
            ApprovalWorkflowStage: The current stage of the workflow.
        """
        first_nonapproved_stage = (
            self.approval_workflow_stages.exclude(state=ApprovalWorkflowStateChoices.APPROVED)
            .order_by("approval_workflow_stage_definition__sequence")
            .first()
        )
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
        # Check of the object under review's content type matches the approval workflow definition's content type
        if self.object_under_review_content_type != self.approval_workflow_definition.model_content_type:
            raise ValidationError(
                f"The content type {self.object_under_review_content_type} of "
                f"the object under review does not match the content type {self.approval_workflow_definition.model_content_type} of the approval workflow definition."
            )

        # TODO need to check of the object fits the model_constraints of the approval workflow
        if self.user:
            self.user_name = self.user.username
        # Check if there is one or more denied/canceled response for this stage instance
        previous_state = self.current_state
        denied_stages = self.approval_workflow_stages.filter(state=ApprovalWorkflowStateChoices.DENIED)
        if denied_stages.exists():
            self.current_state = ApprovalWorkflowStateChoices.DENIED
        else:
            canceled_stages = self.approval_workflow_stages.filter(state=ApprovalWorkflowStateChoices.CANCELED)
            if canceled_stages.exists():
                self.current_state = ApprovalWorkflowStateChoices.CANCELED
            else:
                # Check if all stages are approved
                approved_stages = self.approval_workflow_stages.filter(state=ApprovalWorkflowStateChoices.APPROVED)
                approval_workflow_stage_count = (
                    self.approval_workflow_definition.approval_workflow_stage_definitions.count()
                )
                if approval_workflow_stage_count and approved_stages.count() == approval_workflow_stage_count:
                    self.current_state = ApprovalWorkflowStateChoices.APPROVED

        # If the state is changed to APPROVED or DENIED or CANCELED from PENDING, set the decision date
        if previous_state != self.current_state:
            self.decision_date = timezone.now()
        super().save(*args, **kwargs)

        if previous_state != self.current_state:
            if self.current_state == ApprovalWorkflowStateChoices.APPROVED:
                self.object_under_review.on_workflow_approved(self)
            elif self.current_state == ApprovalWorkflowStateChoices.DENIED:
                self.object_under_review.on_workflow_denied(self)


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ApprovalWorkflowStage(OrganizationalModel):
    """ApprovalWorkflowStage model."""

    approval_workflow = models.ForeignKey(
        to="extras.ApprovalWorkflow",
        related_name="approval_workflow_stages",
        verbose_name="Approval Workflow",
        on_delete=models.CASCADE,
        help_text="Approval workflow to which this stage belongs.",
    )
    approval_workflow_stage_definition = models.ForeignKey(
        to="extras.ApprovalWorkflowStageDefinition",
        related_name="approval_workflow_stages",
        verbose_name="Approval Workflow Stage Definition",
        on_delete=models.CASCADE,
        help_text="Approval workflow stage definition to which this stage belongs.",
    )
    state = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=ApprovalWorkflowStateChoices,
        default=ApprovalWorkflowStateChoices.PENDING,
        help_text="State of the approval workflow stage instance. Eligible values are: Pending, Approved, Denied.",
    )
    decision_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date and time when the decision of approval/denial was made.",
    )
    documentation_static_path = "docs/user-guide/platform-functionality/approval-workflow.html"
    is_version_controlled = False

    is_data_compliance_model = False

    class Meta:
        """Meta class for ApprovalWorkflowStage."""

        verbose_name = "Approval Workflow Stage"
        unique_together = [["approval_workflow", "approval_workflow_stage_definition"]]
        ordering = ["approval_workflow", "approval_workflow_stage_definition__sequence"]

    def __str__(self):
        """Stringify instance."""
        return f"{self.approval_workflow_stage_definition}: {self.state}"

    def get_state_class(self):
        return ApprovalWorkflowStateChoices.CSS_CLASSES.get(self.state)

    @property
    def remaining_approvals(self):
        """
        Calculate the number of remaining approvals needed for this stage instance to be approved.
        Returns:
            int: Number of remaining approvals needed.
        """
        if self.approval_workflow.current_state != ApprovalWorkflowStateChoices.PENDING:
            return 0
        # Get the number of approvers who have already approved this stage instance
        approved_responses = self.approval_workflow_stage_responses.filter(state=ApprovalWorkflowStateChoices.APPROVED)
        # Calculate the number of remaining approvals needed
        return max(0, self.approval_workflow_stage_definition.min_approvers - approved_responses.count())

    @property
    def is_active_stage(self):
        """
        Check if the stage is active.
        An active stage is a stage that is not yet approved or denied.
        Returns:
            bool: True if the stage is active, False otherwise.
        """
        active_stage = self.approval_workflow.active_stage
        # If there is no active stage aka, all stages are approved, return False
        if active_stage is None:
            return False
        # Check if the stage is the active stage and if the stage state is pending
        return self.pk == active_stage.pk and active_stage.state == ApprovalWorkflowStateChoices.PENDING

    @property
    def is_not_done_stage(self):
        """
        Check if the stage is not done (approved or denied).

        Returns:
            bool: True if the stage is not APPROVED or DENIED
        """
        return self.state == ApprovalWorkflowStateChoices.PENDING

    @property
    def users_that_already_approved(self):
        """
        Get the users that have already approved this stage instance.
        Returns:
            list: List of users that have already approved this stage instance.
        """
        return [
            response.user
            for response in self.approval_workflow_stage_responses.filter(state=ApprovalWorkflowStateChoices.APPROVED)
        ]

    @property
    def users_that_already_denied(self):
        """
        Get the users that have already denied this stage instance.
        Returns:
            list: List of users that have already denied this stage instance.
        """
        return [
            response.user
            for response in self.approval_workflow_stage_responses.filter(state=ApprovalWorkflowStateChoices.DENIED)
        ]

    @property
    def should_render_state(self):
        """
        Check if the stage state should be rendered in the UI.
        The stage state should be rendered if the stage is approved or denied or it is currently active and pending.
        Returns:
            bool: True if the stage state should be rendered, False otherwise.
        """
        if self.is_active_stage or self.state in [
            ApprovalWorkflowStateChoices.APPROVED,
            ApprovalWorkflowStateChoices.DENIED,
            ApprovalWorkflowStateChoices.CANCELED,
        ]:
            return True
        return False

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
        # Check if the number of approvers is met
        approved_responses = self.approval_workflow_stage_responses.filter(state=ApprovalWorkflowStateChoices.APPROVED)
        if approved_responses.count() >= self.approval_workflow_stage_definition.min_approvers:
            self.state = ApprovalWorkflowStateChoices.APPROVED

        # Check if there is one or more denied/canceled response for this stage instance
        # If so, set the stage as denied/canceled even tho previously the stage could be approved by enough number of approvers
        denied_responses = self.approval_workflow_stage_responses.filter(state=ApprovalWorkflowStateChoices.DENIED)
        if denied_responses.exists():
            self.state = ApprovalWorkflowStateChoices.DENIED
        else:
            canceled_responses = self.approval_workflow_stage_responses.filter(
                state=ApprovalWorkflowStateChoices.CANCELED
            )
            if canceled_responses.exists():
                self.state = ApprovalWorkflowStateChoices.CANCELED

        # Set the decision date if the state is changed to APPROVED or DENIED
        decision_made = (
            self.state
            in [
                ApprovalWorkflowStateChoices.APPROVED,
                ApprovalWorkflowStateChoices.DENIED,
                ApprovalWorkflowStateChoices.CANCELED,
            ]
            and previous_state != self.state
        )
        if decision_made:
            self.decision_date = timezone.now()
        super().save(*args, **kwargs)

        # Modify the parent ApprovalWorkflow to potentially update its state as well
        # If this stage is approved or denied or canceled.
        if decision_made:
            approval_workflow = self.approval_workflow
            # Check if there is one or more denied response for this stage instance
            denied_or_canceled_stages = approval_workflow.approval_workflow_stages.filter(
                state__in=[ApprovalWorkflowStateChoices.DENIED, ApprovalWorkflowStateChoices.CANCELED]
            )
            if (
                denied_or_canceled_stages.exists()
                and approval_workflow.current_state == ApprovalWorkflowStateChoices.PENDING
            ):
                approval_workflow.save(using=kwargs.get("using"))
            # Check if all stages are approved
            approved_stages = approval_workflow.approval_workflow_stages.filter(
                state=ApprovalWorkflowStateChoices.APPROVED
            )
            if (
                approved_stages.count()
                == approval_workflow.approval_workflow_definition.approval_workflow_stage_definitions.count()
                and approval_workflow.current_state == ApprovalWorkflowStateChoices.PENDING
            ):
                approval_workflow.save(using=kwargs.get("using"))


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class ApprovalWorkflowStageResponse(BaseModel):
    """ApprovalWorkflowStageResponse model."""

    approval_workflow_stage = models.ForeignKey(
        to="extras.ApprovalWorkflowStage",
        related_name="approval_workflow_stage_responses",
        verbose_name="Approval Workflow Stage",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        to=User,
        related_name="approval_workflow_stage_responses",
        verbose_name="User",
        on_delete=models.CASCADE,
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
        help_text="User response to this approval workflow stage instance. Eligible values are: Pending, Comment, Approved, Denied.",
    )
    documentation_static_path = "docs/user-guide/platform-functionality/approval-workflow.html"
    is_version_controlled = False

    is_data_compliance_model = False

    class Meta:
        """Meta class for ApprovalWorkflowStageResponse."""

        db_table = "extras_approvaluserresponse"
        verbose_name = "Approval Workflow Stage Response"
        ordering = ["approval_workflow_stage", "user"]

    def __str__(self):
        """Stringify instance."""
        return f"{self.approval_workflow_stage}: {self.user}"

    def get_state_class(self):
        return ApprovalWorkflowStateChoices.CSS_CLASSES.get(self.state)

    def save(self, *args, **kwargs):
        """
        Override the save method to call save() on the parent ApprovalWorkflowStage as well.
        Args:
            *args: positional arguments
            **kwargs: keyword arguments
        """
        super().save(*args, **kwargs)
        # Call save() on the parent ApprovalWorkflowStage to potentially update its state as well
        # If this stage is approved or denied and the approval workflow stage instance needs to be updated.
        if self.state in [ApprovalWorkflowStateChoices.DENIED, ApprovalWorkflowStateChoices.CANCELED]:
            # Check if the stage instance needs to be updated.
            if self.approval_workflow_stage.state == ApprovalWorkflowStateChoices.PENDING:
                self.approval_workflow_stage.save(using=kwargs.get("using"))
        elif self.state == ApprovalWorkflowStateChoices.APPROVED:
            approved_responses = self.approval_workflow_stage.approval_workflow_stage_responses.filter(
                state=ApprovalWorkflowStateChoices.APPROVED
            )
            approved_response_count = approved_responses.count()
            # Check if the number of approvers is met and the stage instance needs to be updated.
            if (
                approved_response_count == self.approval_workflow_stage.approval_workflow_stage_definition.min_approvers
                and self.approval_workflow_stage.state == ApprovalWorkflowStateChoices.PENDING
            ):
                self.approval_workflow_stage.save(using=kwargs.get("using"))
