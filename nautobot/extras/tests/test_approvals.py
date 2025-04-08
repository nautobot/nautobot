"""Unit tests for Approval Workflow models."""

from django.contrib.contenttypes.models import ContentType

from nautobot.core.testing import APIViewTestCases
from nautobot.extras import models


class ApprovalWorkflowAPITest(APIViewTestCases.APIViewTestCase):
    """ApprovalWorkflow API tests."""

    model = models.ApprovalWorkflow
    choices_fields = ("model_content_type",)

    @classmethod
    def setUpTestData(cls):
        models.ApprovalWorkflow.objects.create(
            name="Test Approval Workflow 1",
            model_content_type=ContentType.objects.get(app_label="extras", model="job"),
            model_constraints={"name": "Bulk Delete Objects"},
        )
        models.ApprovalWorkflow.objects.create(
            name="Test Approval Workflow 2",
            model_content_type=ContentType.objects.get(app_label="extras", model="job"),
            model_constraints={"name": "Bulk Delete Objects"},
        )
        models.ApprovalWorkflow.objects.create(
            name="Test Approval Workflow 3",
            model_content_type=ContentType.objects.get(app_label="extras", model="job"),
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


# TODO Enable the following tests
# class ApprovalWorkflowStageAPITest(APIViewTestCases.APIViewTestCase):
#     """ApprovalWorkflowStage API tests."""

#     model = models.ApprovalWorkflowStage
#     choices_fields = ()

#     @classmethod
#     def setUpTestData(cls):
#         super().setUpTestData()

#         cls.create_data = [
#             {
#                 "approval_workflow": "replaceme",
#                 "sequence_weight": "replaceme",
#                 "name": "replaceme",
#                 "min_approvers": "replaceme",
#                 "denial_message": "replaceme",
#                 "approver_group": "replaceme",
#             },
#             {
#                 "approval_workflow": "replaceme",
#                 "sequence_weight": "replaceme",
#                 "name": "replaceme",
#                 "min_approvers": "replaceme",
#                 "denial_message": "replaceme",
#                 "approver_group": "replaceme",
#             },
#             {
#                 "approval_workflow": "replaceme",
#                 "sequence_weight": "replaceme",
#                 "name": "replaceme",
#                 "min_approvers": "replaceme",
#                 "denial_message": "replaceme",
#                 "approver_group": "replaceme",
#             },
#         ]

#         cls.update_data = {
#             "approval_workflow": "replaceme",
#             "sequence_weight": "replaceme",
#             "name": "replaceme",
#             "min_approvers": "replaceme",
#             "denial_message": "replaceme",
#             "approver_group": "replaceme",
#         }


# class ApprovalWorkflowInstanceAPITest(APIViewTestCases.APIViewTestCase):
#     """ApprovalWorkflowInstance API tests."""

#     model = models.ApprovalWorkflowInstance
#     choices_fields = ("current_state",)

#     @classmethod
#     def setUpTestData(cls):
#         super().setUpTestData()

#         cls.create_data = [
#             {
#                 "approval_workflow": "replaceme",
#                 "object_under_review_content_type": "replaceme",
#                 "object_under_review_object_id": "replaceme",
#                 "current_state": "replaceme",
#             },
#             {
#                 "approval_workflow": "replaceme",
#                 "object_under_review_content_type": "replaceme",
#                 "object_under_review_object_id": "replaceme",
#                 "current_state": "replaceme",
#             },
#             {
#                 "approval_workflow": "replaceme",
#                 "object_under_review_content_type": "replaceme",
#                 "object_under_review_object_id": "replaceme",
#                 "current_state": "replaceme",
#             },
#         ]

#         cls.update_data = {
#             "approval_workflow": "replaceme",
#             "object_under_review_content_type": "replaceme",
#             "object_under_review_object_id": "replaceme",
#             "current_state": "replaceme",
#         }


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
