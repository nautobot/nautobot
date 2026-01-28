from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils.timezone import now

from nautobot.core.templatetags import perms
from nautobot.extras.choices import ApprovalWorkflowStateChoices, JobExecutionType
from nautobot.extras.models import Job, ScheduledJob
from nautobot.extras.models.approvals import ApprovalWorkflow, ApprovalWorkflowDefinition

User = get_user_model()


class NautobotTemplatetagsPermsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="normal",
        )
        self.superuser = User.objects.create_superuser(username="admin")
        self.job_model = Job.objects.get_for_class_path("pass_job.TestPassJob")
        self.job_model.enabled = True
        self.job_model.save()

        self.scheduledjob = ScheduledJob.objects.create(
            name="TessPassJob Scheduled Job",
            task="pass_job.TestPassJob",
            job_model=self.job_model,
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=self.user,
            start_time=now(),
        )
        self.scheduledjob_ct = ContentType.objects.get_for_model(ScheduledJob)

        self.approval_workflow_definition = ApprovalWorkflowDefinition.objects.create(
            name="Test Approval Workflow", model_content_type=self.scheduledjob_ct, weight=0
        )
        self.approval_workflow = ApprovalWorkflow.objects.create(
            approval_workflow_definition=self.approval_workflow_definition,
            object_under_review_content_type=self.scheduledjob_ct,
            object_under_review_object_id=self.scheduledjob.pk,
            current_state=ApprovalWorkflowStateChoices.PENDING,
        )

    def test_can_cancel_as_submitter_and_active(self):
        """Owner of active workflow can cancel"""
        self.approval_workflow.user = self.user
        self.approval_workflow.save()
        self.assertTrue(perms.can_cancel(self.user, self.approval_workflow))

    def test_can_cancel_as_superuser_and_active(self):
        """Superuser can cancel active workflow"""
        # superuser doesn't have to be a submitter
        self.assertNotEqual(self.superuser, self.approval_workflow.user)
        self.assertTrue(perms.can_cancel(self.superuser, self.approval_workflow))

    def test_cannot_cancel_if_not_owner(self):
        """Non-owner, non-superuser cannot cancel"""
        other_user = User.objects.create_user(username="other")
        self.assertFalse(perms.can_cancel(other_user, self.approval_workflow))

    def test_cannot_cancel_if_inactive(self):
        """Inactive workflow cannot be canceled"""
        with self.subTest("Approved approval workflow"):
            self.approval_workflow.current_state = ApprovalWorkflowStateChoices.APPROVED
            self.approval_workflow.save()

            self.assertFalse(perms.can_cancel(self.user, self.approval_workflow))
            self.assertFalse(perms.can_cancel(self.superuser, self.approval_workflow))

        with self.subTest("Denied approval workflow"):
            self.approval_workflow.current_state = ApprovalWorkflowStateChoices.DENIED
            self.approval_workflow.save()

            self.assertFalse(perms.can_cancel(self.user, self.approval_workflow))
            self.assertFalse(perms.can_cancel(self.superuser, self.approval_workflow))

        with self.subTest("Cancel approval workflow"):
            self.approval_workflow.current_state = ApprovalWorkflowStateChoices.CANCELED
            self.approval_workflow.save()

            self.assertFalse(perms.can_cancel(self.user, self.approval_workflow))
            self.assertFalse(perms.can_cancel(self.superuser, self.approval_workflow))

    def test_can_cancel_raises_not_implemented_for_other_models(self):
        """Unsupported instance type raises NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            perms.can_cancel(self.user, object())
