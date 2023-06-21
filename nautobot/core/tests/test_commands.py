# TODO(jathan): This file MUST NOT be merged into Nautobot v2 (next).
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.contenttypes.models import ContentType

from nautobot.utilities.testing import TestCase
from nautobot.dcim.models import VirtualChassis
from nautobot.extras.models import ConfigContext, ConfigContextSchema, ExportTemplate


class PreMigrateCommandTest(TestCase):
    """Test the `nautobot-server pre_migrate` command."""

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
        """Test that duplicate ConfigContext[Schema] objects result in a failure."""
        out, err = self.run_command()

        self.assertIn("All pre-migration checks passed.", out)
        self.assertEqual("", err)

    def test_configcontext_failure(self):
        """Test that duplicate ConfigContext objects result in a failure."""
        ConfigContext.objects.create(name="cc1", data={})
        ConfigContext.objects.create(name="cc1", data={})

        with self.assertRaises(CommandError):
            self.run_command()

    def test_configcontextschema_failure(self):
        """Test that duplicate ConfigContextSchema objects result in a failure."""
        ConfigContextSchema.objects.create(name="ccs1", data_schema={})
        ConfigContextSchema.objects.create(name="ccs1", data_schema={})

        with self.assertRaises(CommandError):
            self.run_command()

    def test_exporttemplate_failure(self):
        """Test that duplicate ExportTemplate objects result in a failure."""
        ct = ContentType.objects.get_for_model(VirtualChassis)
        ExportTemplate.objects.create(content_type=ct, name="et1", template_code="Hello.")
        ExportTemplate.objects.create(content_type=ct, name="et1", template_code="Hello.")

        with self.assertRaises(CommandError):
            self.run_command()

    def test_virtualchassis_failure(self):
        """Test that duplicate VirtualChassis objects result in a failure."""
        VirtualChassis.objects.create(name="vc1")
        VirtualChassis.objects.create(name="vc1")

        with self.assertRaises(CommandError):
            self.run_command()
