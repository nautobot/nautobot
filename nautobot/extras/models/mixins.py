"""
Class-modifying mixins that need to be standalone to avoid circular imports.
"""

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import NoReverseMatch, reverse

from nautobot.core.utils.deprecation import method_deprecated_in_favor_of
from nautobot.core.utils.lookup import get_route_for_model, get_user_from_instance
from nautobot.extras.choices import ApprovalWorkflowStateChoices


class ApprovableModelMixin(models.Model):
    """Abstract mixin for enabling Approval Flow functionality to a given model class."""

    class Meta:
        abstract = True

    is_approval_workflow_model = True

    # Reverse relation so that deleting a ApprovableModelMixin automatically deletes any approval workflows related to it.

    associated_approval_workflows = GenericRelation(
        "extras.ApprovalWorkflow",
        content_type_field="object_under_review_content_type",
        object_id_field="object_under_review_object_id",
        related_query_name="associated_approval_workflows_%(app_label)s_%(class)s",  # e.g. 'associated_object_approval_workflows_dcim_device'
    )

    def get_approval_workflow_url(self):
        """Return the approval workflow URL for this object."""
        route = get_route_for_model(self, "approvalworkflow")

        # Iterate the pk-like fields and try to get a URL, or return None.
        fields = ["pk", "slug"]
        for field in fields:
            if not hasattr(self, field):
                continue

            try:
                return reverse(route, kwargs={field: getattr(self, field)})
            except NoReverseMatch:
                continue

        return None

    def begin_approval_workflow(self):
        """Find and start the appropriate approval workflow for this object."""
        from nautobot.extras.models.approvals import (
            ApprovalWorkflow,
            ApprovalWorkflowDefinition,
            ApprovalWorkflowStage,
            ApprovalWorkflowStageDefinition,
        )  # because of circular import

        # First check if there's already a pending workflow instance
        if self.associated_approval_workflows.filter(current_state=ApprovalWorkflowStateChoices.PENDING).exists():
            return self.associated_approval_workflows.filter(current_state=ApprovalWorkflowStateChoices.PENDING).first()

        # Check if there's a relevant workflow definition
        workflow_definition = ApprovalWorkflowDefinition.objects.find_for_model(self)
        if not workflow_definition:
            return None

        approval_workflow = ApprovalWorkflow.objects.create(
            approval_workflow_definition=workflow_definition,
            object_under_review_content_type=ContentType.objects.get_for_model(self),
            object_under_review_object_id=self.pk,
            current_state=ApprovalWorkflowStateChoices.PENDING,
            user=get_user_from_instance(self),
        )

        # Create workflow stages if the definition has any
        approval_workflow_stage_definitions = ApprovalWorkflowStageDefinition.objects.filter(
            approval_workflow_definition=workflow_definition
        )

        ApprovalWorkflowStage.objects.bulk_create(
            [
                ApprovalWorkflowStage(
                    approval_workflow=approval_workflow,
                    approval_workflow_stage_definition=definition,
                    state=ApprovalWorkflowStateChoices.PENDING,
                )
                for definition in approval_workflow_stage_definitions
            ]
        )

        self.on_workflow_initiated(approval_workflow)

        return approval_workflow

    def on_workflow_initiated(self, approval_workflow):
        """Called when an approval workflow is initiated."""
        raise NotImplementedError("Subclasses must implement `on_workflow_initiated`.")

    def on_workflow_approved(self, approval_workflow):
        """Called when an approval workflow is approved."""
        raise NotImplementedError("Subclasses must implement `on_workflow_approved`.")

    def on_workflow_denied(self, approval_workflow):
        """Called when an approval workflow is denied."""
        raise NotImplementedError("Subclasses must implement `on_workflow_denied`.")

    def has_approval_workflow_definition(self) -> bool:
        from nautobot.extras.models.approvals import ApprovalWorkflowDefinition

        return ApprovalWorkflowDefinition.objects.find_for_model(self) is not None


class ContactMixin(models.Model):
    """Abstract mixin for enabling Contact/Team association to a given model class."""

    class Meta:
        abstract = True

    is_contact_associable_model = True

    # Reverse relation so that deleting a ContactMixin automatically deletes any ContactAssociations related to it.
    associated_contacts = GenericRelation(
        "extras.ContactAssociation",
        content_type_field="associated_object_type",
        object_id_field="associated_object_id",
        related_query_name="associated_contacts_%(app_label)s_%(class)s",  # e.g. 'associated_contacts_dcim_device'
    )


class DynamicGroupMixin:
    """
    DEPRECATED - use DynamicGroupsModelMixin instead if you need to mark a model as supporting Dynamic Groups.

    This is necessary because DynamicGroupMixin was incorrectly not implemented as a subclass of models.Model,
    and so it cannot properly implement Model behaviors like the `static_group_association_set` ReverseRelation.
    However, adding this inheritance to DynamicGroupMixin itself would negatively impact existing migrations.
    So unfortunately our best option is to deprecate this class and gradually convert core and app models alike
    to the new DynamicGroupsModelMixin in its place.

    Adds `dynamic_groups` property to a model to facilitate reversing (cached) DynamicGroup membership.

    If up-to-the-minute accuracy is necessary for your use case, it's up to you to call the
    `DynamicGroup.update_cached_members()` API on any relevant DynamicGroups before accessing this property.

    Other related properties added by this mixin should be considered obsolete.
    """

    is_dynamic_group_associable_model = True

    @property
    def dynamic_groups(self):
        """
        Return a queryset of (cached) `DynamicGroup` objects this instance is a member of.
        """
        from nautobot.extras.models.groups import DynamicGroup

        return DynamicGroup.objects.get_for_object(self)

    @property
    @method_deprecated_in_favor_of(dynamic_groups.fget)
    def dynamic_groups_cached(self):
        """Deprecated - use `self.dynamic_groups` instead."""
        return self.dynamic_groups

    @property
    @method_deprecated_in_favor_of(dynamic_groups.fget)
    def dynamic_groups_list(self):
        """Deprecated - use `list(self.dynamic_groups)` instead."""
        return list(self.dynamic_groups)

    @property
    @method_deprecated_in_favor_of(dynamic_groups.fget)
    def dynamic_groups_list_cached(self):
        """Deprecated - use `list(self.dynamic_groups)` instead."""
        return self.dynamic_groups_list

    # TODO may be able to remove this entirely???
    def get_dynamic_groups_url(self):
        """Return the dynamic groups URL for a given instance."""
        route = get_route_for_model(self, "dynamicgroups")

        # Iterate the pk-like fields and try to get a URL, or return None.
        fields = ["pk", "slug"]
        for field in fields:
            if not hasattr(self, field):
                continue

            try:
                return reverse(route, kwargs={field: getattr(self, field)})
            except NoReverseMatch:
                continue

        return None


class DynamicGroupsModelMixin(DynamicGroupMixin, models.Model):
    """
    Add this to models to make them fully support Dynamic Groups.
    """

    class Meta:
        abstract = True

    # Reverse relation so that deleting a DynamicGroupMixin automatically deletes any related StaticGroupAssociations
    static_group_association_set = GenericRelation(  # not "static_group_associations" as that'd collide on DynamicGroup
        "extras.StaticGroupAssociation",
        content_type_field="associated_object_type",
        object_id_field="associated_object_id",
        related_query_name="static_group_association_set_%(app_label)s_%(class)s",
    )


class NotesMixin:
    """
    Adds a `notes` property that returns a queryset of `Notes` membership.
    """

    @property
    def notes(self):
        """Return a `Notes` queryset for this instance."""
        from nautobot.extras.models.models import Note

        if not hasattr(self, "_notes_queryset"):
            queryset = Note.objects.get_for_object(self)
            self._notes_queryset = queryset

        return self._notes_queryset

    def get_notes_url(self, api=False):
        """Return the notes URL for a given instance."""
        route = get_route_for_model(self, "notes", api=api)

        # Iterate the pk-like fields and try to get a URL, or return None.
        fields = ["pk", "slug"]
        for field in fields:
            if not hasattr(self, field):
                continue

            try:
                return reverse(route, kwargs={field: getattr(self, field)})
            except NoReverseMatch:
                continue

        return None


class SavedViewMixin(models.Model):
    """Abstract mixin for enabling Saved View functionality to a given model class."""

    class Meta:
        abstract = True

    is_saved_view_model = True


class DataComplianceModelMixin:
    """
    Adds a `get_data_compliance_url` that can be applied to instances.
    """

    is_data_compliance_model = True

    def get_data_compliance_url(self, api=False):
        """Return the data compliance URL for a given instance."""
        # If is_data_compliance_model overridden should allow to opt out
        if not self.is_data_compliance_model:
            return None
        route = get_route_for_model(self, "data-compliance", api=api)

        # Iterate the pk-like fields and try to get a URL, or return None.
        fields = ["pk", "slug"]
        for field in fields:
            if not hasattr(self, field):
                continue

            try:
                return reverse(route, kwargs={field: getattr(self, field)})
            except NoReverseMatch:
                continue

        return None
