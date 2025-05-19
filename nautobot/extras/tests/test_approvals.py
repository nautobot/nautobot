"""Unit tests for Approval Workflow models."""

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType

from nautobot.core.testing import APIViewTestCases
from nautobot.extras import choices, models
from nautobot.users.models import User


class ApprovalWorkflowTestMixin:
    """Mixin class for ApprovalWorkflow tests."""

    @classmethod
    def setUpTestData(cls):
        job_ct = ContentType.objects.get(app_label="extras", model="job")
        jobs = list(models.Job.objects.all())
        cls.approver_group_1 = Group.objects.create(name="Approver Group 1")
        cls.approver_group_2 = Group.objects.create(name="Approver Group 2")
        users = list(User.objects.all())
        for user in users:
            user.groups.add(cls.approver_group_1)
            user.groups.add(cls.approver_group_2)

        cls.approval_workflow_def_1 = models.ApprovalWorkflowDefinition.objects.create(
            name="Test Approval Workflow Definition 1",
            model_content_type=job_ct,
        )
        cls.approval_workflow_def_2 = models.ApprovalWorkflowDefinition.objects.create(
            name="Test Approval Workflow Definition 2",
            model_content_type=job_ct,
            model_constraints={"name": "Bulk Delete Objects"},
        )
        cls.approval_workflow_def_3 = models.ApprovalWorkflowDefinition.objects.create(
            name="Test Approval Workflow Definition 3",
            model_content_type=ContentType.objects.get(app_label="extras", model="job"),
            model_constraints={"name": "Bulk Delete Objects"},
        )
        cls.approval_workflow_def_4 = models.ApprovalWorkflowDefinition.objects.create(
            name="Test Approval Workflow Definition 4",
            model_content_type=job_ct,
            model_constraints={"name": "Bulk Delete Objects"},
        )
        cls.approval_workflow_def_5 = models.ApprovalWorkflowDefinition.objects.create(
            name="Test Approval Workflow Definition 5",
            model_content_type=job_ct,
            model_constraints={"name": "Bulk Delete Objects"},
        )
        cls.approval_workflow_1_instance_1 = models.ApprovalWorkflow.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            object_under_review_content_type=job_ct,
            object_under_review_object_id=jobs[0].pk,
            current_state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        cls.approval_workflow_1_instance_2 = models.ApprovalWorkflow.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_2,
            object_under_review_content_type=job_ct,
            object_under_review_object_id=jobs[1].pk,
            current_state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        cls.approval_workflow_1_instance_3 = models.ApprovalWorkflow.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            object_under_review_content_type=job_ct,
            object_under_review_object_id=jobs[2].pk,
            current_state=choices.ApprovalWorkflowStateChoices.APPROVED,
        )
        cls.approval_workflow_1_instance_4 = models.ApprovalWorkflow.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_2,
            object_under_review_content_type=job_ct,
            object_under_review_object_id=jobs[3].pk,
            current_state=choices.ApprovalWorkflowStateChoices.DENIED,
        )
        cls.approval_workflow_1_instance_5 = models.ApprovalWorkflow.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_2,
            object_under_review_content_type=job_ct,
            object_under_review_object_id=jobs[4].pk,
            current_state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        cls.approval_workflow_1_stage_def_1 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            weight=100,
            name="Test Approval Workflow 1 Stage 1",
            min_approvers=2,
            denial_message="Stage 1 Denial Message",
            approver_group=cls.approver_group_1,
        )
        cls.approval_workflow_1_stage_def_2 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            weight=200,
            name="Test Approval Workflow 1 Stage 2",
            min_approvers=2,
            denial_message="Stage 2 Denial Message",
            approver_group=cls.approver_group_2,
        )
        cls.approval_workflow_1_stage_def_3 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            weight=300,
            name="Test Approval Workflow 1 Stage 3",
            min_approvers=2,
            denial_message="Stage 3 Denial Message",
            approver_group=cls.approver_group_2,
        )
        cls.approval_workflow_1_stage_def_4 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            weight=400,
            name="Test Approval Workflow 1 Stage 4",
            min_approvers=2,
            denial_message="Stage 4 Denial Message",
            approver_group=cls.approver_group_1,
        )
        cls.approval_workflow_1_stage_def_5 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            weight=500,
            name="Test Approval Workflow 1 Stage 5",
            min_approvers=2,
            denial_message="Stage 5 Denial Message",
            approver_group=cls.approver_group_2,
        )
        cls.approval_workflow_1_stage_def_6 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            weight=600,
            name="Test Approval Workflow 1 Stage 6",
            min_approvers=2,
            denial_message="Stage 6 Denial Message",
            approver_group=cls.approver_group_1,
        )
        cls.approval_workflow_2_stage_def_1 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_2,
            weight=100,
            name="Test Approval Workflow 2 Stage 1",
            min_approvers=2,
            denial_message="Stage 1 Denial Message",
            approver_group=cls.approver_group_1,
        )
        cls.approval_workflow_2_stage_def_2 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_2,
            weight=200,
            name="Test Approval Workflow 2 Stage 2",
            min_approvers=2,
            denial_message="Stage 2 Denial Message",
            approver_group=cls.approver_group_2,
        )
        cls.approval_workflow_2_stage_def_3 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_2,
            weight=300,
            name="Test Approval Workflow 2 Stage 3",
            min_approvers=2,
            denial_message="Stage 3 Denial Message",
            approver_group=cls.approver_group_2,
        )
        cls.approval_workflow_1_stage_instance_1 = models.ApprovalWorkflowStage.objects.create(
            approval_workflow=cls.approval_workflow_1_instance_1,
            approval_workflow_stage_definition=cls.approval_workflow_1_stage_def_1,
            state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        cls.approval_workflow_1_stage_instance_2 = models.ApprovalWorkflowStage.objects.create(
            approval_workflow=cls.approval_workflow_1_instance_1,
            approval_workflow_stage_definition=cls.approval_workflow_1_stage_def_2,
            state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        cls.approval_workflow_1_stage_instance_3 = models.ApprovalWorkflowStage.objects.create(
            approval_workflow=cls.approval_workflow_1_instance_1,
            approval_workflow_stage_definition=cls.approval_workflow_1_stage_def_3,
            state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        cls.approval_workflow_2_stage_instance_1 = models.ApprovalWorkflowStage.objects.create(
            approval_workflow=cls.approval_workflow_1_instance_2,
            approval_workflow_stage_definition=cls.approval_workflow_2_stage_def_1,
            state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        cls.approval_workflow_2_stage_instance_2 = models.ApprovalWorkflowStage.objects.create(
            approval_workflow=cls.approval_workflow_1_instance_2,
            approval_workflow_stage_definition=cls.approval_workflow_2_stage_def_2,
            state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        cls.approval_workflow_2_stage_instance_3 = models.ApprovalWorkflowStage.objects.create(
            approval_workflow=cls.approval_workflow_1_instance_2,
            approval_workflow_stage_definition=cls.approval_workflow_2_stage_def_3,
            state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        models.ApprovalWorkflowStageResponse.objects.create(
            approval_workflow_stage=cls.approval_workflow_1_stage_instance_1,
            user=User.objects.first(),
            comments="Approved by user 1",
            state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        models.ApprovalWorkflowStageResponse.objects.create(
            approval_workflow_stage=cls.approval_workflow_1_stage_instance_2,
            user=User.objects.last(),
            comments="Denied by user 2",
            state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        models.ApprovalWorkflowStageResponse.objects.create(
            approval_workflow_stage=cls.approval_workflow_1_stage_instance_1,
            user=User.objects.last(),
            comments="Approved by user 2",
            state=choices.ApprovalWorkflowStateChoices.PENDING,
        )


class ApprovalWorkflowDefinitionAPITest(ApprovalWorkflowTestMixin, APIViewTestCases.APIViewTestCase):
    """ApprovalWorkflowDefinition API tests."""

    model = models.ApprovalWorkflowDefinition
    choices_fields = ("model_content_type",)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "name": "Approval Workflow Definition 1",
                "model_content_type": "extras.job",
                "model_constraints": {"name": "Bulk Delete Objects"},
            },
            {
                "name": "Approval Workflow Definition 2",
                "model_content_type": "extras.job",
                "model_constraints": {},
            },
            {
                "name": "Approval Workflow Definition 3",
                "model_content_type": "extras.scheduledjob",
                "model_constraints": {"name": "Bulk Delete Objects"},
            },
        ]

        cls.update_data = {
            "name": "Approval Workflow Definition 4",
            "model_content_type": "extras.scheduledjob",
            "model_constraints": {"approval_required": True},
        }


class ApprovalWorkflowStageDefinitionAPITest(ApprovalWorkflowTestMixin, APIViewTestCases.APIViewTestCase):
    """ApprovalWorkflowStageDefinition API tests."""

    model = models.ApprovalWorkflowStageDefinition
    choices_fields = ()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "approval_workflow_definition": cls.approval_workflow_def_2.pk,
                "weight": 400,
                "name": "Test Approval Workflow 2 Stage 4 Definition",
                "min_approvers": 3,
                "denial_message": "Stage 4 Denial Message",
                "approver_group": cls.approver_group_1.pk,
            },
            {
                "approval_workflow_definition": cls.approval_workflow_def_2.pk,
                "weight": 500,
                "name": "Test Approval Workflow 2 Stage 5 Definition",
                "min_approvers": 2,
                "denial_message": "Stage 5 Denial Message",
                "approver_group": cls.approver_group_2.pk,
            },
            {
                "approval_workflow_definition": cls.approval_workflow_def_2.pk,
                "weight": 600,
                "name": "Test Approval Workflow 2 Stage 6 Definition",
                "min_approvers": 1,
                "denial_message": "Stage 6 Denial Message",
                "approver_group": cls.approver_group_1.pk,
            },
        ]

        cls.update_data = {
            "weight": 700,
            "approval_workflow_definition": cls.approval_workflow_def_2.pk,
            "min_approvers": 4,
            "denial_message": "Updated Denial Message",
            "approver_group": cls.approver_group_1.pk,
        }


class ApprovalWorkflowAPITest(ApprovalWorkflowTestMixin, APIViewTestCases.APIViewTestCase):
    """ApprovalWorkflow API tests."""

    model = models.ApprovalWorkflow
    choices_fields = (
        "current_state",
        "object_under_review_content_type",
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        jobs = list(models.Job.objects.all())

        cls.create_data = [
            {
                "approval_workflow_definition": cls.approval_workflow_def_1.pk,
                "object_under_review_content_type": "extras.job",
                "object_under_review_object_id": jobs[5].pk,
                "current_state": choices.ApprovalWorkflowStateChoices.PENDING,
            },
            {
                "approval_workflow_definition": cls.approval_workflow_def_1.pk,
                "object_under_review_content_type": "extras.job",
                "object_under_review_object_id": jobs[6].pk,
                "current_state": choices.ApprovalWorkflowStateChoices.PENDING,
            },
            {
                "approval_workflow_definition": cls.approval_workflow_def_1.pk,
                "object_under_review_content_type": "extras.job",
                "object_under_review_object_id": jobs[7].pk,
                "current_state": choices.ApprovalWorkflowStateChoices.PENDING,
            },
        ]

        cls.update_data = {
            "approval_workflow_definition": cls.approval_workflow_def_2.pk,
            "current_state": choices.ApprovalWorkflowStateChoices.APPROVED,
        }


class ApprovalWorkflowStageAPITest(ApprovalWorkflowTestMixin, APIViewTestCases.APIViewTestCase):
    """ApprovalWorkflowStage API tests."""

    model = models.ApprovalWorkflowStage
    choices_fields = ("state",)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "approval_workflow": cls.approval_workflow_1_instance_1.pk,
                "approval_workflow_stage_definition": cls.approval_workflow_1_stage_def_4.pk,
                "state": choices.ApprovalWorkflowStateChoices.PENDING,
            },
            {
                "approval_workflow": cls.approval_workflow_1_instance_1.pk,
                "approval_workflow_stage_definition": cls.approval_workflow_1_stage_def_5.pk,
                "state": choices.ApprovalWorkflowStateChoices.APPROVED,
            },
            {
                "approval_workflow": cls.approval_workflow_1_instance_1.pk,
                "approval_workflow_stage_definition": cls.approval_workflow_1_stage_def_6.pk,
                "state": choices.ApprovalWorkflowStateChoices.DENIED,
            },
        ]

        cls.update_data = {
            "state": choices.ApprovalWorkflowStateChoices.APPROVED,
        }


class ApprovalWorkflowStageResponseAPITest(ApprovalWorkflowTestMixin, APIViewTestCases.APIViewTestCase):
    """ApprovalWorkflowStageResponse API tests."""

    model = models.ApprovalWorkflowStageResponse
    choices_fields = ("state",)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        users = list(User.objects.all())

        cls.create_data = [
            {
                "approval_workflow_stage": cls.approval_workflow_1_stage_instance_1.pk,
                "user": users[3].pk,
                "comments": "Approved by user 1",
                "state": choices.ApprovalWorkflowStateChoices.APPROVED,
            },
            {
                "approval_workflow_stage": cls.approval_workflow_1_stage_instance_2.pk,
                "user": users[4].pk,
                "comments": "Approved by user 2",
                "state": choices.ApprovalWorkflowStateChoices.APPROVED,
            },
            {
                "approval_workflow_stage": cls.approval_workflow_1_stage_instance_3.pk,
                "user": users[4].pk,
                "comments": "Denied by user 1",
                "state": choices.ApprovalWorkflowStateChoices.DENIED,
            },
        ]

        cls.update_data = {
            "comments": "Comments updated",
            "state": choices.ApprovalWorkflowStateChoices.APPROVED,
        }
