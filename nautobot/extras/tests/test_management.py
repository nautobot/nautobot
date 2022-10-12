"""Test cases for extras management code."""

from django.apps import apps

from nautobot.extras.management import populate_status_choices
from nautobot.extras.models import Status
from nautobot.utilities.testing import TestCase


class StatusManagementTestCase(TestCase):
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
        # and so long as their slugs are unchanged, no new statuses should be created
        status = Status.objects.get(slug="active")
        status.name = "Really Active"
        status.validated_save()

        status = Status.objects.get(slug="planned")
        status.color = "12ab34"
        status.validated_save()

        status = Status.objects.get(slug="container")
        status.description = "I'm a little teapot"
        status.validated_save()

        populate_status_choices(apps=apps, schema_editor=None)
        self.assertEqual(Status.objects.count(), initial_statuses_count)

    def test_populate_status_choices_error_handling(self):
        """
        Verify that populate_status_choices() handles Status slug change when its name still matches a default Status.
        """
        initial_statuses_count = Status.objects.count()
        status = Status.objects.get(slug="active")
        status.slug = "active2"
        status.validated_save()
        # Note that status.name is still "Active", which also must be globally unique.
        # populate_status_choices will first attempt to get_or_create(slug="active", defaults={"name": "Active"}),
        # which will fail due to the non-unique name; it should then fall back to
        # get_or_create(name="Active", defaults={"slug": "active"}), which will succeed, leaving the status unchanged.
        populate_status_choices(apps=apps, schema_editor=None)
        status.refresh_from_db()
        self.assertEqual(status.slug, "active2")
        self.assertEqual(initial_statuses_count, Status.objects.count())
