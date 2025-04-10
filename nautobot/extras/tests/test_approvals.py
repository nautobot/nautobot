"""Unit tests for Approval Workflow models."""

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType

from nautobot.core.testing import APIViewTestCases
from nautobot.extras import choices, models


class ApprovalWorkflowAPITest(APIViewTestCases.APIViewTestCase):
    """ApprovalWorkflow API tests."""

    model = models.ApprovalWorkflow
    choices_fields = ("model_content_type",)

    @classmethod
    def setUpTestData(cls):
        job_ct = ContentType.objects.get(app_label="extras", model="job")
        models.ApprovalWorkflow.objects.create(
            name="Test Approval Workflow 1",
            model_content_type=job_ct,
            model_constraints={"name": "Bulk Delete Objects"},
        )
        models.ApprovalWorkflow.objects.create(
            name="Test Approval Workflow 2",
            model_content_type=job_ct,
            model_constraints={"name": "Bulk Delete Objects"},
        )
        models.ApprovalWorkflow.objects.create(
            name="Test Approval Workflow 3",
            model_content_type=job_ct,
            model_constraints={"name": "Bulk Delete Objects"},
        )

        cls.create_data = [
            {
                "name": "Approval Workflow 1",
                "model_content_type": "extras.job",
                "model_constraints": {"name": "Bulk Delete Objects"},
            },
            {
                "name": "Approval Workflow 2",
                "model_content_type": "extras.job",
                "model_constraints": {},
            },
            {
                "name": "Approval Workflow 3",
                "model_content_type": "extras.scheduledjob",
                "model_constraints": {"name": "Bulk Delete Objects"},
            },
        ]

        cls.update_data = {
            "name": "Approval Workflow 4",
            "model_content_type": "extras.scheduledjob",
            "model_constraints": {"approval_required": True},
        }


class ApprovalWorkflowStageAPITest(APIViewTestCases.APIViewTestCase):
    """ApprovalWorkflowStage API tests."""

    model = models.ApprovalWorkflowStage
    choices_fields = ()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        job_ct = ContentType.objects.get(app_label="extras", model="job")
        approval_workflow_1 = models.ApprovalWorkflow.objects.create(
            name="Test Approval Workflow 1",
            model_content_type=job_ct,
            model_constraints={"name": "Bulk Delete Objects"},
        )
        approval_workflow_2 = models.ApprovalWorkflow.objects.create(
            name="Test Approval Workflow 2",
            model_content_type=ContentType.objects.get(app_label="extras", model="scheduledjob"),
            model_constraints={"name": "Bulk Delete Objects"},
        )
        approver_group_1 = Group.objects.create(name="Approver Group 1")
        approver_group_2 = Group.objects.create(name="Approver Group 2")
        models.ApprovalWorkflowStage.objects.create(
            approval_workflow=approval_workflow_1,
            weight=100,
            name="Test Approval Workflow 1 Stage 1",
            min_approvers=2,
            denial_message="Stage 1 Denial Message",
            approver_group=approver_group_1,
        )
        models.ApprovalWorkflowStage.objects.create(
            approval_workflow=approval_workflow_1,
            weight=200,
            name="Test Approval Workflow 1 Stage 2",
            min_approvers=2,
            denial_message="Stage 2 Denial Message",
            approver_group=approver_group_2,
        )
        models.ApprovalWorkflowStage.objects.create(
            approval_workflow=approval_workflow_1,
            weight=300,
            name="Test Approval Workflow 1 Stage 3",
            min_approvers=1,
            denial_message="Stage 3 Denial Message",
            approver_group=approver_group_2,
        )

        cls.create_data = [
            {
                "approval_workflow": approval_workflow_2.pk,
                "weight": 100,
                "name": "Test Approval Workflow 2 Stage 1",
                "min_approvers": 3,
                "denial_message": "Stage 1 Denial Message",
                "approver_group": approver_group_1.pk,
            },
            {
                "approval_workflow": approval_workflow_2.pk,
                "weight": 200,
                "name": "Test Approval Workflow 2 Stage 2",
                "min_approvers": 2,
                "denial_message": "Stage 2 Denial Message",
                "approver_group": approver_group_2.pk,
            },
            {
                "approval_workflow": approval_workflow_2.pk,
                "weight": 300,
                "name": "Test Approval Workflow 2 Stage 3",
                "min_approvers": 1,
                "denial_message": "Stage 3 Denial Message",
                "approver_group": approver_group_1.pk,
            },
        ]

        cls.update_data = {
            "approval_workflow": approval_workflow_2.pk,
            "min_approvers": 4,
            "denial_message": "Updated Denial Message",
            "approver_group": approver_group_1.pk,
        }


class ApprovalWorkflowInstanceAPITest(APIViewTestCases.APIViewTestCase):
    """ApprovalWorkflowInstance API tests."""

    model = models.ApprovalWorkflowInstance
    choices_fields = (
        "current_state",
        "object_under_review_content_type",
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        job_ct = ContentType.objects.get(app_label="extras", model="job")
        approval_workflow_1 = models.ApprovalWorkflow.objects.create(
            name="Test Approval Workflow 1",
            model_content_type=job_ct,
        )
        approval_workflow_2 = models.ApprovalWorkflow.objects.create(
            name="Test Approval Workflow 2",
            model_content_type=job_ct,
        )
        jobs = list(models.Job.objects.all())
        job_1 = jobs[0]
        job_2 = jobs[1]
        models.ApprovalWorkflowInstance.objects.create(
            approval_workflow=approval_workflow_1,
            object_under_review_content_type=job_ct,
            object_under_review_object_id=job_1.pk,
            current_state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        models.ApprovalWorkflowInstance.objects.create(
            approval_workflow=approval_workflow_1,
            object_under_review_content_type=job_ct,
            object_under_review_object_id=job_2.pk,
            current_state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        models.ApprovalWorkflowInstance.objects.create(
            approval_workflow=approval_workflow_1,
            object_under_review_content_type=job_ct,
            object_under_review_object_id=job_2.pk,
            current_state=choices.ApprovalWorkflowStateChoices.PENDING,
        )

        cls.create_data = [
            {
                "approval_workflow": approval_workflow_1.pk,
                "object_under_review_content_type": "extras.job",
                "object_under_review_object_id": jobs[3].pk,
                "current_state": choices.ApprovalWorkflowStateChoices.PENDING,
            },
            {
                "approval_workflow": approval_workflow_1.pk,
                "object_under_review_content_type": "extras.job",
                "object_under_review_object_id": jobs[4].pk,
                "current_state": choices.ApprovalWorkflowStateChoices.PENDING,
            },
            {
                "approval_workflow": approval_workflow_1.pk,
                "object_under_review_content_type": "extras.job",
                "object_under_review_object_id": jobs[3].pk,
                "current_state": choices.ApprovalWorkflowStateChoices.PENDING,
            },
        ]

        cls.update_data = {
            "approval_workflow": approval_workflow_2.pk,
            "current_state": choices.ApprovalWorkflowStateChoices.APPROVED,
        }


# TODO Enable the following tests
# class ApprovalWorkflowStageInstanceAPITest(APIViewTestCases.APIViewTestCase):
#     """ApprovalWorkflowStageInstance API tests."""

#     model = models.ApprovalWorkflowStageInstance
#     choices_fields = ("state",)

#     @classmethod
#     def setUpTestData(cls):
#         super().setUpTestData()

#         cls.create_data = [
#             {
#                 "approval_workflow_instance": "replaceme",
#                 "approval_workflow_stage": "replaceme",
#                 "state": "replaceme",
#                 "decision_date": "replaceme",
#             },
#             {
#                 "approval_workflow_instance": "replaceme",
#                 "approval_workflow_stage": "replaceme",
#                 "state": "replaceme",
#                 "decision_date": "replaceme",
#             },
#             {
#                 "approval_workflow_instance": "replaceme",
#                 "approval_workflow_stage": "replaceme",
#                 "state": "replaceme",
#                 "decision_date": "replaceme",
#             },
#         ]

#         cls.update_data = {
#             "approval_workflow_instance": "replaceme",
#             "approval_workflow_stage": "replaceme",
#             "state": "replaceme",
#             "decision_date": "replaceme",
#         }


# class ApprovalWorkflowStageInstanceResponseAPITest(APIViewTestCases.APIViewTestCase):
#     """ApprovalWorkflowStageInstanceResponse API tests."""

#     model = models.ApprovalWorkflowStageInstanceResponse
#     choices_fields = ("state",)

#     @classmethod
#     def setUpTestData(cls):
#         super().setUpTestData()

#         cls.create_data = [
#             {
#                 "approval_workflow_stage_instance": "replaceme",
#                 "user": "replaceme",
#                 "comments": "replaceme",
#                 "state": "replaceme",
#             },
#             {
#                 "approval_workflow_stage_instance": "replaceme",
#                 "user": "replaceme",
#                 "comments": "replaceme",
#                 "state": "replaceme",
#             },
#             {
#                 "approval_workflow_stage_instance": "replaceme",
#                 "user": "replaceme",
#                 "comments": "replaceme",
#                 "state": "replaceme",
#             },
#         ]

#         cls.update_data = {
#             "approval_workflow_stage_instance": "replaceme",
#             "user": "replaceme",
#             "comments": "replaceme",
#             "state": "replaceme",
#         }
