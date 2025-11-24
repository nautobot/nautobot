"""Unit tests for Approval Workflow models."""

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now

from nautobot.core.jobs import BulkDeleteObjects, ExportObjectList
from nautobot.core.testing import APITestCase, APIViewTestCases, TestCase
from nautobot.extras import choices, models
from nautobot.users.models import User


class ApprovalWorkflowTestMixin:
    """Mixin class for ApprovalWorkflow tests."""

    @classmethod
    def setUpTestData(cls):
        scheduled_job_ct = ContentType.objects.get_for_model(models.ScheduledJob)
        scheduled_jobs = list(models.ScheduledJob.objects.all())
        cls.approver_group_1 = Group.objects.create(name="Approver Group 1")
        cls.approver_group_2 = Group.objects.create(name="Approver Group 2")
        users = list(User.objects.all())
        for user in users:
            user.groups.add(cls.approver_group_1)
            user.groups.add(cls.approver_group_2)

        job_model = models.Job.objects.get_for_class_path(BulkDeleteObjects.class_path)
        scheduled_jobs = [
            models.ScheduledJob.objects.create(
                name=f"Bulk Delete Objects Scheduled Job {i}",
                task=BulkDeleteObjects.class_path,
                job_model=job_model,
                interval=choices.JobExecutionType.TYPE_IMMEDIATELY,
                user=users[0],
                start_time=now(),
            )
            for i in range(8)
        ]
        cls.approval_workflow_def_1 = models.ApprovalWorkflowDefinition.objects.create(
            name="Test Approval Workflow Definition 1",
            model_content_type=scheduled_job_ct,
            weight=0,
        )
        cls.approval_workflow_def_2 = models.ApprovalWorkflowDefinition.objects.create(
            name="Test Approval Workflow Definition 2",
            model_content_type=scheduled_job_ct,
            model_constraints={"name": "Bulk Delete Objects"},
            weight=1,
        )
        cls.approval_workflow_def_3 = models.ApprovalWorkflowDefinition.objects.create(
            name="Test Approval Workflow Definition 3",
            model_content_type=scheduled_job_ct,
            model_constraints={"name": "Bulk Delete Objects"},
            weight=2,
        )
        cls.approval_workflow_def_4 = models.ApprovalWorkflowDefinition.objects.create(
            name="Test Approval Workflow Definition 4",
            model_content_type=scheduled_job_ct,
            model_constraints={"name": "Bulk Delete Objects"},
            weight=3,
        )
        cls.approval_workflow_def_5 = models.ApprovalWorkflowDefinition.objects.create(
            name="Test Approval Workflow Definition 5",
            model_content_type=scheduled_job_ct,
            model_constraints={"name": "Bulk Delete Objects"},
            weight=4,
        )
        cls.approval_workflow_1_instance_1 = models.ApprovalWorkflow.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            object_under_review_content_type=scheduled_job_ct,
            object_under_review_object_id=scheduled_jobs[0].pk,
            current_state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        cls.approval_workflow_1_instance_2 = models.ApprovalWorkflow.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_2,
            object_under_review_content_type=scheduled_job_ct,
            object_under_review_object_id=scheduled_jobs[1].pk,
            current_state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        cls.approval_workflow_1_instance_3 = models.ApprovalWorkflow.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            object_under_review_content_type=scheduled_job_ct,
            object_under_review_object_id=scheduled_jobs[2].pk,
            current_state=choices.ApprovalWorkflowStateChoices.APPROVED,
        )
        cls.approval_workflow_1_instance_4 = models.ApprovalWorkflow.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_2,
            object_under_review_content_type=scheduled_job_ct,
            object_under_review_object_id=scheduled_jobs[3].pk,
            current_state=choices.ApprovalWorkflowStateChoices.DENIED,
        )
        cls.approval_workflow_1_instance_5 = models.ApprovalWorkflow.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_2,
            object_under_review_content_type=scheduled_job_ct,
            object_under_review_object_id=scheduled_jobs[4].pk,
            current_state=choices.ApprovalWorkflowStateChoices.PENDING,
        )
        cls.approval_workflow_1_stage_def_1 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            sequence=100,
            name="Test Approval Workflow 1 Stage 1",
            min_approvers=2,
            denial_message="Stage 1 Denial Message",
            approver_group=cls.approver_group_1,
        )
        cls.approval_workflow_1_stage_def_2 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            sequence=200,
            name="Test Approval Workflow 1 Stage 2",
            min_approvers=2,
            denial_message="Stage 2 Denial Message",
            approver_group=cls.approver_group_2,
        )
        cls.approval_workflow_1_stage_def_3 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            sequence=300,
            name="Test Approval Workflow 1 Stage 3",
            min_approvers=2,
            denial_message="Stage 3 Denial Message",
            approver_group=cls.approver_group_2,
        )
        cls.approval_workflow_1_stage_def_4 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            sequence=400,
            name="Test Approval Workflow 1 Stage 4",
            min_approvers=2,
            denial_message="Stage 4 Denial Message",
            approver_group=cls.approver_group_1,
        )
        cls.approval_workflow_1_stage_def_5 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            sequence=500,
            name="Test Approval Workflow 1 Stage 5",
            min_approvers=2,
            denial_message="Stage 5 Denial Message",
            approver_group=cls.approver_group_2,
        )
        cls.approval_workflow_1_stage_def_6 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_1,
            sequence=600,
            name="Test Approval Workflow 1 Stage 6",
            min_approvers=2,
            denial_message="Stage 6 Denial Message",
            approver_group=cls.approver_group_1,
        )
        cls.approval_workflow_2_stage_def_1 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_2,
            sequence=100,
            name="Test Approval Workflow 2 Stage 1",
            min_approvers=2,
            denial_message="Stage 1 Denial Message",
            approver_group=cls.approver_group_1,
        )
        cls.approval_workflow_2_stage_def_2 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_2,
            sequence=200,
            name="Test Approval Workflow 2 Stage 2",
            min_approvers=2,
            denial_message="Stage 2 Denial Message",
            approver_group=cls.approver_group_2,
        )
        cls.approval_workflow_2_stage_def_3 = models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=cls.approval_workflow_def_2,
            sequence=300,
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
                "model_content_type": "extras.scheduledjob",
                "model_constraints": {"name": "Bulk Delete Objects"},
                "weight": 5,
            },
            {
                "name": "Approval Workflow Definition 2",
                "model_content_type": "extras.scheduledjob",
                "model_constraints": {},
                "weight": 6,
            },
            {
                "name": "Approval Workflow Definition 3",
                "model_content_type": "extras.scheduledjob",
                "model_constraints": {"name": "Bulk Delete Objects"},
                "weight": 7,
            },
        ]

        cls.update_data = {
            "name": "Approval Workflow Definition 4",
            "model_content_type": "extras.scheduledjob",
            "model_constraints": {"approval_required": True},
        }


class ApprovalWorkflowDefinitionManagerTest(TestCase):
    def setUp(self):
        scheduled_job_ct = ContentType.objects.get_for_model(models.ScheduledJob)
        job_model = models.Job.objects.get_for_class_path(BulkDeleteObjects.class_path)
        self.scheduled_job = models.ScheduledJob.objects.create(
            name="Bulk Delete Objects Scheduled Job",
            task=BulkDeleteObjects.class_path,
            job_model=job_model,
            interval=choices.JobExecutionType.TYPE_IMMEDIATELY,
            user=User.objects.first(),
            start_time=now(),
        )
        self.approval_workflow_defs = [
            models.ApprovalWorkflowDefinition.objects.create(
                name=f"Test Approval Workflow Definition {i}",
                model_content_type=scheduled_job_ct,
                weight=len(range(4)) - 1 - i,  # first with highest weight
            )
            for i in range(4)
        ]

    def test_find_for_model(self):
        """Test that the workflow definition with the highest weight and no constraints is returned."""
        self.assertEqual(
            models.ApprovalWorkflowDefinition.objects.find_for_model(self.scheduled_job),
            self.approval_workflow_defs[0],
        )
        self.assertEqual(self.approval_workflow_defs[0].weight, 3)

    def test_find_for_model_with_filter_match_constraints(self):
        """Test that a workflow definition with filter matching constraints is correctly returned."""
        self.approval_workflow_defs[0].model_constraints = {
            "job_model__name__in": ["Bulk Delete Objects", "Export Object List"]
        }
        self.approval_workflow_defs[0].save()
        self.assertEqual(
            models.ApprovalWorkflowDefinition.objects.find_for_model(self.scheduled_job),
            self.approval_workflow_defs[0],
        )
        self.assertEqual(self.approval_workflow_defs[0].weight, 3)

        export_job_model = models.Job.objects.get_for_class_path(ExportObjectList.class_path)
        export_scheduled_job = models.ScheduledJob.objects.create(
            name="Export Scheduled Job",
            task=ExportObjectList.class_path,
            job_model=export_job_model,
            interval=choices.JobExecutionType.TYPE_IMMEDIATELY,
            user=User.objects.first(),
            start_time=now(),
        )
        self.assertEqual(
            models.ApprovalWorkflowDefinition.objects.find_for_model(export_scheduled_job),
            self.approval_workflow_defs[0],
        )
        self.assertEqual(self.approval_workflow_defs[0].weight, 3)

    def test_find_for_model_with_exact_match_constraints(self):
        """Test that a workflow definition with exact matching constraints is correctly returned."""
        self.approval_workflow_defs[0].model_constraints = {"name": "Bulk Delete Objects Scheduled Job"}
        self.approval_workflow_defs[0].save()
        self.assertEqual(
            models.ApprovalWorkflowDefinition.objects.find_for_model(self.scheduled_job),
            self.approval_workflow_defs[0],
        )
        self.assertEqual(self.approval_workflow_defs[0].weight, 3)

    def test_find_for_model_returns_highest_weight_when_all_match(self):
        """
        Test that when all workflow definitions match the model instance,
        the one with the highest weight is returned.
        """
        # Set all definitions to have matching constraints
        for definition in self.approval_workflow_defs:
            definition.model_constraints = {"name": "Bulk Delete Objects Scheduled Job"}
            definition.save()

        self.assertEqual(
            models.ApprovalWorkflowDefinition.objects.find_for_model(self.scheduled_job),
            self.approval_workflow_defs[0],
        )
        self.assertEqual(self.approval_workflow_defs[0].weight, 3)

    def test_find_for_model_skips_unmatched_constraints_and_returns_next_without_constraints(self):
        """
        Test that if the highest weight workflow definition has unmatched constraints,
        the method skips it and returns the next one with no constraints.
        """
        # Set constraints on the highest weight definition that do not match the instance
        self.approval_workflow_defs[0].model_constraints = {"name": "Non Matching Name"}
        self.approval_workflow_defs[0].save()

        # Ensure the next workflow has no constraints
        self.approval_workflow_defs[1].model_constraints = {}
        self.approval_workflow_defs[1].save()

        self.assertEqual(
            models.ApprovalWorkflowDefinition.objects.find_for_model(self.scheduled_job),
            self.approval_workflow_defs[1],
        )
        self.assertEqual(self.approval_workflow_defs[1].weight, 2)

    def test_find_for_model_matches_lower_weight_if_higher_fails(self):
        """
        Test that if the highest weight workflow definition's constraints don't match,
        the next matching lower-weight definition is returned.
        """
        self.approval_workflow_defs[0].model_constraints = {"name": "Non Matching Name"}
        self.approval_workflow_defs[0].save()

        self.approval_workflow_defs[1].model_constraints = {"name": "Bulk Delete Objects Scheduled Job"}
        self.approval_workflow_defs[1].save()

        self.assertEqual(
            models.ApprovalWorkflowDefinition.objects.find_for_model(self.scheduled_job),
            self.approval_workflow_defs[1],
        )
        self.assertEqual(self.approval_workflow_defs[1].weight, 2)

    def test_find_for_model_ignores_constraints_matching_different_instance(self):
        """
        Test that a workflow definition is not returned if its constraints match a different instance
        rather than the one provided to the method.
        """
        models.ScheduledJob.objects.create(
            name="Other Job",
            task=BulkDeleteObjects.class_path,
            job_model=self.scheduled_job.job_model,
            interval=choices.JobExecutionType.TYPE_IMMEDIATELY,
            user=User.objects.first(),
            start_time=now(),
        )

        for approval_workflow_def in self.approval_workflow_defs:
            approval_workflow_def.model_constraints = {"name": "Other Job"}
            approval_workflow_def.save()

        self.assertIsNone(models.ApprovalWorkflowDefinition.objects.find_for_model(self.scheduled_job))

    def test_find_for_model_returns_none_if_no_definitions(self):
        """Test that None is returned if there are no workflow definitions available."""
        models.ApprovalWorkflowDefinition.objects.all().delete()
        self.assertIsNone(models.ApprovalWorkflowDefinition.objects.find_for_model(self.scheduled_job))


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
                "sequence": 400,
                "name": "Test Approval Workflow 2 Stage 4 Definition",
                "min_approvers": 3,
                "denial_message": "Stage 4 Denial Message",
                "approver_group": cls.approver_group_1.pk,
            },
            {
                "approval_workflow_definition": cls.approval_workflow_def_2.pk,
                "sequence": 500,
                "name": "Test Approval Workflow 2 Stage 5 Definition",
                "min_approvers": 2,
                "denial_message": "Stage 5 Denial Message",
                "approver_group": cls.approver_group_2.pk,
            },
            {
                "approval_workflow_definition": cls.approval_workflow_def_2.pk,
                "sequence": 600,
                "name": "Test Approval Workflow 2 Stage 6 Definition",
                "min_approvers": 1,
                "denial_message": "Stage 6 Denial Message",
                "approver_group": cls.approver_group_1.pk,
            },
        ]

        cls.update_data = {
            "sequence": 700,
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
        scheduled_jobs = list(models.ScheduledJob.objects.all())

        cls.create_data = [
            {
                "approval_workflow_definition": cls.approval_workflow_def_1.pk,
                "object_under_review_content_type": "extras.scheduledjob",
                "object_under_review_object_id": scheduled_jobs[5].pk,
                "current_state": choices.ApprovalWorkflowStateChoices.PENDING,
            },
            {
                "approval_workflow_definition": cls.approval_workflow_def_1.pk,
                "object_under_review_content_type": "extras.scheduledjob",
                "object_under_review_object_id": scheduled_jobs[6].pk,
                "current_state": choices.ApprovalWorkflowStateChoices.PENDING,
            },
            {
                "approval_workflow_definition": cls.approval_workflow_def_1.pk,
                "object_under_review_content_type": "extras.scheduledjob",
                "object_under_review_object_id": scheduled_jobs[7].pk,
                "current_state": choices.ApprovalWorkflowStateChoices.PENDING,
            },
        ]

        cls.update_data = {
            "approval_workflow_definition": cls.approval_workflow_def_2.pk,
            "current_state": choices.ApprovalWorkflowStateChoices.APPROVED,
        }


class ApprovalWorkflowTriggerAPITest(APITestCase):
    """
    Test suite for verifying the trigger and approval handling of approval workflows.
    """

    def setUp(self):
        super().setUp()
        approver_group_1 = Group.objects.create(name="Approver Group 1")
        users = list(User.objects.all())
        for user in users:
            user.groups.add(approver_group_1)
        self.job_model = models.Job.objects.get_for_class_path("pass_job.TestPassJob")
        self.content_type = ContentType.objects.get_for_model(models.ScheduledJob)
        self.approval_workflow_def = models.ApprovalWorkflowDefinition.objects.create(
            name="Test Approval Workflow Definition",
            model_content_type=self.content_type,
        )
        models.ApprovalWorkflowStageDefinition.objects.create(
            approval_workflow_definition=self.approval_workflow_def,
            sequence=100,
            name="Test Approval Workflow Stage 1",
            min_approvers=2,
            denial_message="Stage 1 Denial Message",
            approver_group=approver_group_1,
        )

    def test_no_initialization_approval_workflow_for_scheduled_job(self):
        """
        Test that creating a ScheduledJob without approval workflow definition doesn't initialize an approval workflow.

        The test verifies:
        - No approval workflows definition exist for ScheduledJob before creation.
        - No approval workflows exist for ScheduledJob before creation.
        - An approval workflow is not created automatically upon ScheduledJob creation.
        - The ScheduledJob is not associated with the approval workflow.
        - The ScheduledJob is created with `enabled=True`.
        """
        models.ApprovalWorkflowDefinition.objects.filter(model_content_type=self.content_type).delete()
        self.assertFalse(
            models.ApprovalWorkflowDefinition.objects.filter(model_content_type=self.content_type).exists()
        )
        self.assertFalse(
            models.ApprovalWorkflow.objects.filter(object_under_review_content_type=self.content_type).exists()
        )

        scheduled_job = models.ScheduledJob.objects.create(
            name="test0",
            task="pass_job.TestPassJob",
            job_model=self.job_model,
            interval=choices.JobExecutionType.TYPE_IMMEDIATELY,
            user=self.user,
            start_time=now(),
        )
        self.assertFalse(scheduled_job.associated_approval_workflows.exists())
        self.assertFalse(
            models.ApprovalWorkflow.objects.filter(object_under_review_content_type=self.content_type).exists()
        )
        self.assertTrue(scheduled_job.enabled)

    def test_initialization_approval_workflow_for_scheduled_job(self):
        """
        Test that creating a ScheduledJob initializes an approval workflow.

        The test verifies:
        - No approval workflows exist for ScheduledJob before creation.
        - An approval workflow is created automatically upon ScheduledJob creation.
        - Approval workflow stages are created automatically upon ScheduledJob creation
        - The ScheduledJob is associated with the approval workflow.
        - The ScheduledJob is created with `enabled=False`.
        """
        self.assertFalse(
            models.ApprovalWorkflow.objects.filter(object_under_review_content_type=self.content_type).exists()
        )

        scheduled_job = models.ScheduledJob.objects.create(
            name="test1",
            task="pass_job.TestPassJob",
            job_model=self.job_model,
            interval=choices.JobExecutionType.TYPE_IMMEDIATELY,
            user=self.user,
            start_time=now(),
        )
        self.assertTrue(scheduled_job.associated_approval_workflows.exists())
        self.assertIsNone(scheduled_job.decision_date)
        approval_workflow = scheduled_job.associated_approval_workflows.first()
        self.assertEqual(approval_workflow.approval_workflow_stages.count(), 1)

    def test_approval_workflow_approved_for_scheduled_job(self):
        """
        Test that approval workflow approval enables the scheduled job.

        This test ensures:
        - No approval workflows exist for ScheduledJob before creation.
        - An approval workflow and its stages are automatically created when a ScheduledJob is created.
        - The ScheduledJob is associated with the created approval workflow.
        - The ScheduledJob is initially created with `enabled=False`.
        - When the active approval workflow stage is approved and the workflow is saved,
        the workflow's state transitions to APPROVED.
        - Once the workflow is approved, the ScheduledJob is automatically enabled.
        """
        scheduled_job = models.ScheduledJob.objects.create(
            name="test2",
            task="pass_job.TestPassJob",
            job_model=self.job_model,
            interval=choices.JobExecutionType.TYPE_IMMEDIATELY,
            user=self.user,
            start_time=now(),
        )
        self.assertIsNone(scheduled_job.decision_date)

        approval_workflow = scheduled_job.associated_approval_workflows.first()
        self.assertEqual(approval_workflow.approval_workflow_stages.count(), 1)
        active_stage = approval_workflow.active_stage
        active_stage.state = choices.ApprovalWorkflowStateChoices.APPROVED
        active_stage.save()
        approval_workflow.save()
        self.assertEqual(approval_workflow.current_state, choices.ApprovalWorkflowStateChoices.APPROVED)

        scheduled_job.refresh_from_db()
        self.assertEqual(scheduled_job.decision_date, approval_workflow.decision_date)

    def test_approval_workflow_denied_for_scheduled_job(self):
        """
        Test that denial of an approval workflow keeps the scheduled job disabled.

        This test ensures:
        - An approval workflow and its stages are automatically created when a ScheduledJob is created.
        - The ScheduledJob is initially created with `enabled=False`.
        - When the active approval workflow stage is marked as DENIED and the workflow is saved,
        the workflow's state transitions to DENIED.
        - A DENIED workflow prevents the ScheduledJob from being enabled.
        """
        scheduled_job = models.ScheduledJob.objects.create(
            name="test3",
            task="pass_job.TestPassJob",
            job_model=self.job_model,
            interval=choices.JobExecutionType.TYPE_IMMEDIATELY,
            user=self.user,
            start_time=now(),
        )
        self.assertIsNone(scheduled_job.decision_date)
        approval_workflow = scheduled_job.associated_approval_workflows.first()
        self.assertEqual(approval_workflow.approval_workflow_stages.count(), 1)
        active_stage = approval_workflow.active_stage
        active_stage.state = choices.ApprovalWorkflowStateChoices.DENIED
        active_stage.save()
        approval_workflow.save()
        self.assertEqual(approval_workflow.current_state, choices.ApprovalWorkflowStateChoices.DENIED)
        scheduled_job.refresh_from_db()
        self.assertEqual(scheduled_job.decision_date, approval_workflow.decision_date)


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
            {
                "approval_workflow_stage": cls.approval_workflow_2_stage_instance_1.pk,
                "user": users[4].pk,
                "comments": "Denied by user 1",
                "state": choices.ApprovalWorkflowStateChoices.CANCELED,
            },
        ]

        cls.update_data = {
            "comments": "Comments updated",
            "state": choices.ApprovalWorkflowStateChoices.APPROVED,
        }
