from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from nautobot.extras.group_sync import group_sync

User = get_user_model()


@mock.patch("nautobot.extras.group_sync.SUPERUSER_GROUPS", ["nautobot_admin"])
@mock.patch("nautobot.extras.group_sync.STAFF_GROUPS", ["nautobot_admin", "nautobot_staff"])
class GroupSyncTestCase(TestCase):
    """Tests for the SSO group_sync pipeline function."""

    def setUp(self):
        self.user = User.objects.create(username="ssouser")

    def test_oauth2_oidc_response(self):
        """Group claims at the top level of the response (OAuth2/OIDC) are synced."""
        response = {"groups": ["ops", "nautobot_admin"]}

        group_sync("ssouser", user=self.user, response=response)

        self.user.refresh_from_db()
        self.assertEqual(
            sorted(self.user.groups.values_list("name", flat=True)),
            ["nautobot_admin", "ops"],
        )
        self.assertTrue(self.user.is_superuser)
        self.assertTrue(self.user.is_staff)

    def test_saml_response(self):
        """Group attributes nested under "attributes" (SAML) are synced. Regression test for #6887."""
        response = {"attributes": {"groups": ["ops", "nautobot_staff"]}}

        group_sync("ssouser", user=self.user, response=response)

        self.user.refresh_from_db()
        self.assertEqual(
            sorted(self.user.groups.values_list("name", flat=True)),
            ["nautobot_staff", "ops"],
        )
        self.assertFalse(self.user.is_superuser)
        self.assertTrue(self.user.is_staff)

    def test_top_level_claim_preferred_over_saml_attributes(self):
        """When both shapes are present, the top-level claim wins."""
        response = {"groups": ["ops"], "attributes": {"groups": ["nautobot_admin"]}}

        group_sync("ssouser", user=self.user, response=response)

        self.user.refresh_from_db()
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["ops"])
        self.assertFalse(self.user.is_superuser)

    def test_response_without_groups(self):
        """A response without any group claims leaves the user unchanged."""
        self.user.groups.add(Group.objects.create(name="existing"))

        group_sync("ssouser", user=self.user, response={"attributes": {"other": "value"}})

        self.user.refresh_from_db()
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["existing"])
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.is_staff)

    def test_no_response(self):
        """A missing response does not raise and leaves the user unchanged."""
        group_sync("ssouser", user=self.user, response=None)

        self.user.refresh_from_db()
        self.assertEqual(self.user.groups.count(), 0)
