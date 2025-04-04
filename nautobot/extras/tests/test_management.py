"""Test cases for extras management code."""

from django.apps import apps

from nautobot.core.testing import TestCase
from nautobot.extras.management import populate_role_choices, populate_status_choices
from nautobot.extras.models import Role, Status


class MetadataManagementTestCase(TestCase):
    """Tests for the populate_status_choices helper function."""

    def test_populate_status_choices_idempotent(self):
        """
        Verify that populate_status_choices() is idempotent and can be re-run safely.
        """
        initial_statuses_count = Status.objects.count()
        # Should be safe to re-run when statuses already exist
        populate_status_choices(apps=apps, schema_editor=None)
        self.assertEqual(Status.objects.count(), initial_statuses_count)

        # Should be safe to re-run when default statuses have been modified,
        # and so long as their names are unchanged, no new statuses should be created

        status = Status.objects.get(name="Planned")
        status.color = "12ab34"
        status.validated_save()

        status = Status.objects.get(name="Deprecated")
        status.description = "I'm a little teapot"
        status.validated_save()

        populate_status_choices(apps=apps, schema_editor=None)
        self.assertEqual(Status.objects.count(), initial_statuses_count)

    def test_populate_role_choices_idempotent(self):
        """
        Verify that populate_role_choices() is idempotent and can be re-run safely.
        """
        initial_roles_count = Role.objects.count()
        # Should be safe to re-run when roles already exist
        populate_role_choices(apps=apps, schema_editor=None)
        self.assertEqual(Role.objects.count(), initial_roles_count)

        # Should be safe to re-run when default statuses have been modified,
        # and so long as their names are unchanged, no new statuses should be created

        role = Role.objects.get(name="Administrative")
        role.color = "12ab34"
        role.validated_save()

        role = Role.objects.get(name="Billing")
        role.description = "I'm a little teapot"
        role.validated_save()

        populate_role_choices(apps=apps, schema_editor=None)
        self.assertEqual(Role.objects.count(), initial_roles_count)
