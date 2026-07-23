from io import StringIO
from pathlib import Path
import tempfile

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
import yaml

from nautobot.core.testing import TestCase, TransactionTestCase
from nautobot.dcim.models import Device
from nautobot.extras.models import Status


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


class ImportExportObjectsCommandsTestCase(TransactionTestCase):
    """Test the import_objects / export_objects management commands end-to-end."""

    databases = ("default", "job_logs")

    def test_export_then_import_round_trip(self):
        """Export a status to a file, edit it, and import it back as an in-place update."""
        self.user.is_superuser = True
        self.user.save()
        status = Status.objects.create(name="test_cmd_status", color="111111")
        status.content_types.set([ContentType.objects.get_for_model(Device)])

        out = StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "statuses.csv"
            call_command(
                "export_objects",
                "extras.status",
                "-u",
                self.user.username,
                "--filter",
                "name=test_cmd_status",
                "-o",
                str(output_path),
                stdout=out,
            )
            content = output_path.read_text(encoding="utf-8-sig")
            self.assertTrue(content.startswith("# nautobot-import: match_fields=name"), content)

            output_path.write_text(content.replace("111111", "222222"), encoding="utf-8")
            call_command("import_objects", "extras.status", str(output_path), "-u", self.user.username, stdout=out)

        status.refresh_from_db()
        self.assertEqual(status.color, "222222")
        self.assertEqual(Status.objects.filter(name="test_cmd_status").count(), 1)
