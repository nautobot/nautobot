from unittest import mock

from django.test import override_settings

from nautobot.core.branching import BranchContext
from nautobot.core.testing import TestCase
from nautobot.extras.models import Status
from nautobot.extras.models.jobs import JOB_LOGS


class BranchContextTest(TestCase):
    """Test cases for the BranchContext context manager."""

    databases = ["default", JOB_LOGS]

    def test_non_branched_default(self):
        active_status = Status.objects.get(name="Active")

        with BranchContext():
            self.assertEqual(active_status, Status.objects.get(name="Active"))

        with BranchContext(branch_name=None):
            self.assertEqual(active_status, Status.objects.get(name="Active"))

        with BranchContext(branch_name=None, user=self.user):
            self.assertEqual(active_status, Status.objects.get(name="Active"))

        with BranchContext(branch_name=None, user=self.user, using=JOB_LOGS):
            self.assertEqual(active_status, Status.objects.get(name="Active"))

        with BranchContext(branch_name=None, user=self.user, using=JOB_LOGS, autocommit=False):
            self.assertEqual(active_status, Status.objects.get(name="Active"))

        # If a branch is requested, we should log a warning and ignore it
        with self.assertLogs("nautobot.core.branching", level="WARNING") as cm:
            with BranchContext(branch_name="fake-branch"):
                self.assertEqual(active_status, Status.objects.get(name="Active"))
        self.assertIn(
            "WARNING:nautobot.core.branching:nautobot_version_control is not installed, ignoring requested branch fake-branch",
            cm.output,
        )

    @override_settings(PLUGINS=["nautobot_version_control"])
    def test_vc_no_branch(self):
        with mock.patch.dict(
            "sys.modules",
            {
                "nautobot_version_control.middleware": mock.MagicMock(),
                "nautobot_version_control.utils": mock.MagicMock(),
            },
        ):
            from nautobot_version_control.middleware import AutoDoltCommit  # pylint: disable=import-error
            from nautobot_version_control.utils import active_branch, checkout_branch  # pylint: disable=import-error

            with BranchContext():
                Status.objects.get(name="Active")

            active_branch.assert_not_called()
            checkout_branch.assert_not_called()
            AutoDoltCommit.assert_not_called()

    @override_settings(PLUGINS=["nautobot_version_control"])
    def test_vc_changed_branch(self):
        with mock.patch.dict(
            "sys.modules",
            {
                "nautobot_version_control.middleware": mock.MagicMock(),
                "nautobot_version_control.utils": mock.MagicMock(),
            },
        ):
            from nautobot_version_control.middleware import AutoDoltCommit  # pylint: disable=import-error
            from nautobot_version_control.utils import active_branch, checkout_branch  # pylint: disable=import-error

            active_branch.return_value = "main"

            with BranchContext(branch_name="fake-branch", autocommit=False):
                Status.objects.get(name="Active")

            active_branch.assert_called_once_with(using="default")
            checkout_branch.assert_any_call("fake-branch", using="default")
            checkout_branch.assert_any_call("main", using="default")
            AutoDoltCommit.assert_not_called()

    @override_settings(PLUGINS=["nautobot_version_control"])
    def test_vc_unchanged_branch(self):
        with mock.patch.dict(
            "sys.modules",
            {
                "nautobot_version_control.middleware": mock.MagicMock(),
                "nautobot_version_control.utils": mock.MagicMock(),
            },
        ):
            from nautobot_version_control.middleware import AutoDoltCommit  # pylint: disable=import-error
            from nautobot_version_control.utils import active_branch, checkout_branch  # pylint: disable=import-error

            active_branch.return_value = "fake-branch"

            with BranchContext(branch_name="fake-branch", autocommit=False):
                Status.objects.get(name="Active")

            active_branch.assert_called_once_with(using="default")
            checkout_branch.assert_not_called()
            AutoDoltCommit.assert_not_called()

    @override_settings(PLUGINS=["nautobot_version_control"])
    def test_vc_changed_branch_with_autocommit(self):
        with mock.patch.dict(
            "sys.modules",
            {
                "nautobot_version_control.middleware": mock.MagicMock(),
                "nautobot_version_control.utils": mock.MagicMock(),
            },
        ):
            from nautobot_version_control.middleware import AutoDoltCommit  # pylint: disable=import-error
            from nautobot_version_control.utils import active_branch, checkout_branch  # pylint: disable=import-error

            active_branch.return_value = "main"

            with BranchContext(branch_name="fake-branch", autocommit=True, user=self.user):
                Status.objects.get(name="Active")

            active_branch.assert_called_once_with(using="default")
            checkout_branch.assert_any_call("fake-branch", using="default")
            AutoDoltCommit.assert_called_once_with(user=self.user)
            AutoDoltCommit.return_value.__enter__.assert_called_once()
            AutoDoltCommit.return_value.__exit__.assert_called_once()
            checkout_branch.assert_any_call("main", using="default")

    @override_settings(PLUGINS=["nautobot_version_control"])
    def test_vc_contextmanager_behavior(self):
        """Make sure BranchContext is a proper context-manager, i.e. it cleans up even in error cases."""

        with mock.patch.dict(
            "sys.modules",
            {
                "nautobot_version_control.middleware": mock.MagicMock(),
                "nautobot_version_control.utils": mock.MagicMock(),
            },
        ):
            from nautobot_version_control.middleware import AutoDoltCommit  # pylint: disable=import-error
            from nautobot_version_control.utils import active_branch, checkout_branch  # pylint: disable=import-error

            active_branch.return_value = "main"

            with self.assertRaises(RuntimeError):
                with BranchContext(branch_name="fake-branch", autocommit=True, using=JOB_LOGS):
                    raise RuntimeError("Oh no!")

            active_branch.assert_called_once_with(using=JOB_LOGS)
            checkout_branch.assert_any_call("fake-branch", using=JOB_LOGS)
            AutoDoltCommit.assert_called_once_with(user=None)
            AutoDoltCommit.return_value.__enter__.assert_called_once()
            AutoDoltCommit.return_value.__exit__.assert_called_once()
            checkout_branch.assert_any_call("main", using=JOB_LOGS)
