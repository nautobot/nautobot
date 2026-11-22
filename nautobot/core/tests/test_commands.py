from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
import yaml

from nautobot.core.testing import TestCase


class ManagementCommandTestCase(TestCase):
    """Test case for core management commands."""

    def setUp(self):
        """Initialize user and client."""
        super().setUpNautobot()
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)

    def test_generate_performance_test_endpoints(self):
        """Test the generate_performance_test_endpoints management command."""
        out = StringIO()
        call_command("generate_performance_test_endpoints", stdout=out)
        endpoints_dict = yaml.safe_load(out.getvalue())["endpoints"]
        for view_name, value in endpoints_dict.items():
            for endpoint in value:
                with self.subTest(endpoint=endpoint):
                    response = self.client.get(endpoint, follow=True)
                    self.assertHttpStatus(
                        response,
                        200,
                        f"{view_name}: {endpoint} returns status Code {response.status_code} instead of 200",
                    )


class PostUpgradeCommandTest(SimpleTestCase):
    """Tests for the post_upgrade management command's argument handling (no database required)."""

    # All steps except migrate disabled, so tests can focus on the migrate call.
    ALL_DISABLE_FLAGS = [
        "--no-clear-cache",
        "--no-clearsessions",
        "--no-collectstatic",
        "--no-remove-stale-contenttypes",
        "--no-trace-paths",
        "--no-send-installation-metrics",
        "--no-refresh-content-type-cache",
        "--no-refresh-dynamic-group-member-caches",
    ]

    @mock.patch("nautobot.core.management.commands.post_upgrade.call_command")
    def test_migrate_all_apps_by_default(self, mock_call_command):
        """Without --migrate-app, migrate is called without an app label (all apps)."""
        call_command("post_upgrade", *self.ALL_DISABLE_FLAGS)

        mock_call_command.assert_any_call(
            "migrate",
            skip_checks=False,
            interactive=False,
            traceback=False,
            verbosity=1,
        )

    @mock.patch("nautobot.core.management.commands.post_upgrade.call_command")
    def test_migrate_app_limits_migrations_to_that_app(self, mock_call_command):
        """--migrate-app dcim passes the app label through to the migrate command."""
        call_command("post_upgrade", "--migrate-app", "dcim", *self.ALL_DISABLE_FLAGS)

        mock_call_command.assert_any_call(
            "migrate",
            "dcim",
            skip_checks=False,
            interactive=False,
            traceback=False,
            verbosity=1,
        )
        # and no unscoped migrate call happened
        for call in mock_call_command.call_args_list:
            if call.args and call.args[0] == "migrate":
                self.assertEqual(call.args[1], "dcim")

    def test_migrate_app_rejects_unknown_app_label(self):
        """An unknown app label raises CommandError before any migration runs."""
        with self.assertRaisesMessage(CommandError, "No installed app with label 'no_such_app'"):
            call_command("post_upgrade", "--migrate-app", "no_such_app", *self.ALL_DISABLE_FLAGS)

    @mock.patch("nautobot.core.management.commands.post_upgrade.call_command")
    def test_migrate_app_ignored_when_migrate_disabled(self, mock_call_command):
        """--no-migrate wins over --migrate-app: no migrate call at all."""
        call_command("post_upgrade", "--migrate-app", "dcim", "--no-migrate", *self.ALL_DISABLE_FLAGS)

        mock_call_command.assert_not_called()

    @mock.patch("nautobot.core.management.commands.post_upgrade.call_command")
    def test_no_migrate_app_means_no_migrate_call(self, mock_call_command):
        """--no-migrate alone skips the migrate step."""
        call_command("post_upgrade", "--no-migrate", *self.ALL_DISABLE_FLAGS)

        mock_call_command.assert_not_called()
