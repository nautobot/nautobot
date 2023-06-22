# TODO(jathan): This file MUST NOT be merged into Nautobot v2 (next).
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.contenttypes.models import ContentType

from nautobot.utilities.testing import TestCase
from nautobot.dcim.models import VirtualChassis
from nautobot.extras.datasources.registry import get_datasource_contents
from nautobot.extras.models import ConfigContext, ConfigContextSchema, ExportTemplate, GitRepository


class PreMigrateCommandTest(TestCase):
    """Test the `nautobot-server pre_migrate` command."""

    def setUp(self):
        super().setUp()
        self.git_repo = GitRepository(
            name="Test Git Repository",
            slug="test_git_repo",
            remote_url="http://localhost/git.git",
            # Provide everything we know we can provide
            provided_contents=[entry.content_identifier for entry in get_datasource_contents("extras.gitrepository")],
        )
        self.git_repo.save(trigger_resync=False)

    def run_command(self, *args):
        out = StringIO()
        err = StringIO()
        call_command(
            "pre_migrate",
            *args,
            stdout=out,
            stderr=err,
        )

        return (out.getvalue(), err.getvalue())

    def test_success(self):
        """Test that the command passes with most common data."""
        out, err = self.run_command()

        self.assertIn("All pre-migration checks passed.", out)
        self.assertEqual("", err)

    def test_configcontext_failure(self):
        """Test that duplicate ConfigContext objects result in a failure."""
        ConfigContext(name="cc1", data={"foo": "bar"}).validated_save()
        ConfigContext(name="cc1", data={"foo": "bar"}, owner=self.git_repo).validated_save()

        with self.assertRaises(CommandError):
            self.run_command()

    def test_configcontextschema_failure(self):
        """Test that duplicate ConfigContextSchema objects result in a failure."""
        ConfigContextSchema(
            name="ccs1", data_schema={"type": "object", "properties": {"b": {"type": "integer"}}}
        ).validated_save()
        ConfigContextSchema(
            name="ccs1", data_schema={"type": "object", "properties": {"b": {"type": "integer"}}}, owner=self.git_repo
        ).validated_save()

        with self.assertRaises(CommandError):
            self.run_command()

    def test_exporttemplate_failure(self):
        """Test that duplicate ExportTemplate objects result in a failure."""
        ct = ContentType.objects.get_for_model(VirtualChassis)
        ExportTemplate(content_type=ct, name="et1", template_code="Hello.").validated_save()
        ExportTemplate(content_type=ct, name="et1", template_code="Hello.", owner=self.git_repo).validated_save()

        with self.assertRaises(CommandError):
            self.run_command()

    def test_virtualchassis_failure(self):
        """Test that duplicate VirtualChassis objects result in a failure."""
        VirtualChassis.objects.create(name="vc1")
        VirtualChassis.objects.create(name="vc1")

        with self.assertRaises(CommandError):
            self.run_command()
