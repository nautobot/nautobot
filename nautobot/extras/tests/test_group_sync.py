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

    def _make_privileged_user(self):
        """Give `self.user` the group memberships and flags of a previously successful sync."""
        self.user.groups.add(Group.objects.create(name="existing"))
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()

    def assertRevoked(self):
        self.user.refresh_from_db()
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), [])
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.is_staff)

    def assertRetained(self):
        self.user.refresh_from_db()
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["existing"])
        self.assertTrue(self.user.is_superuser)
        self.assertTrue(self.user.is_staff)

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

    def test_empty_top_level_claim_falls_back_to_saml_attributes(self):
        """An empty top-level claim does not shadow a populated SAML attribute of the same name."""
        response = {"groups": [], "attributes": {"groups": ["nautobot_admin"]}}

        group_sync("ssouser", user=self.user, response=response)

        self.user.refresh_from_db()
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["nautobot_admin"])
        self.assertTrue(self.user.is_superuser)

    def test_partial_group_membership_demotes(self):
        """Groups the user is no longer a member of are removed and the flags are recomputed."""
        self._make_privileged_user()

        group_sync("ssouser", user=self.user, response={"groups": ["ops"]})

        self.user.refresh_from_db()
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["ops"])
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.is_staff)

    def test_empty_top_level_claim_revokes(self):
        """An empty top-level group claim is authoritative and revokes all memberships and flags."""
        self._make_privileged_user()

        group_sync("ssouser", user=self.user, response={"groups": []})

        self.assertRevoked()

    def test_empty_saml_attribute_revokes(self):
        """An empty SAML group attribute is authoritative and revokes all memberships and flags."""
        self._make_privileged_user()

        group_sync("ssouser", user=self.user, response={"attributes": {"groups": []}})

        self.assertRevoked()

    def test_response_without_groups(self):
        """An absent group claim leaves the user unchanged, and says so with a warning rather than silently."""
        self._make_privileged_user()

        with self.assertLogs("nautobot.extras.group_sync", level="WARNING") as logs:
            group_sync("ssouser", user=self.user, response={"attributes": {"other": "value"}})

        self.assertRetained()
        self.assertIn("Did not receive a 'groups' claim from SSO for user ssouser", "\n".join(logs.output))

    def test_no_response(self):
        """A missing response does not raise and leaves the user unchanged."""
        self._make_privileged_user()

        group_sync("ssouser", user=self.user, response=None)

        self.assertRetained()

    def test_no_user(self):
        """A missing user does not raise."""
        group_sync("ssouser", user=None, response={"groups": ["ops"]})

        self.assertFalse(Group.objects.filter(name="ops").exists())

    def test_all_groups_synced_by_default(self):
        """With SSO_SYNC_GROUPS unset, every group in the claim is synced."""
        group_sync("ssouser", user=self.user, response={"groups": ["ops", "noise", "more_noise"]})

        self.user.refresh_from_db()
        self.assertEqual(
            sorted(self.user.groups.values_list("name", flat=True)),
            ["more_noise", "noise", "ops"],
        )

    def test_response_values_not_logged(self):
        """Only claim names are logged; the pipeline response also carries the backend's token data."""
        response = {"access_token": "s3cr3t-token", "id_token": "s3cr3t-id-token", "email": "user@example.com"}

        with self.assertLogs("nautobot.extras.group_sync", level="DEBUG") as logs:
            group_sync("ssouser", user=self.user, response=response)

        output = "\n".join(logs.output)
        self.assertNotIn("s3cr3t-token", output)
        self.assertNotIn("s3cr3t-id-token", output)
        self.assertNotIn("user@example.com", output)
        # The claim names are still reported, so a misconfigured SSO_CLAIMS_GROUP can be diagnosed
        self.assertIn("access_token", output)


@mock.patch("nautobot.extras.group_sync.SUPERUSER_GROUPS", ["nautobot_admin"])
@mock.patch("nautobot.extras.group_sync.STAFF_GROUPS", ["nautobot_staff"])
@mock.patch("nautobot.extras.group_sync.SYNC_GROUPS", ["ops", "neteng"])
class GroupSyncFilterTestCase(TestCase):
    """Tests for restricting which groups are synced via SSO_SYNC_GROUPS."""

    def setUp(self):
        self.user = User.objects.create(username="ssouser")

    def test_only_listed_groups_are_synced(self):
        """Groups omitted from SSO_SYNC_GROUPS are neither assigned nor created in Nautobot."""
        group_sync("ssouser", user=self.user, response={"groups": ["ops", "orgb_eng", "orgb_ops"]})

        self.user.refresh_from_db()
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["ops"])
        self.assertFalse(Group.objects.filter(name__startswith="orgb_").exists())

    def test_saml_attributes_are_filtered(self):
        """The filter applies to group attributes nested under "attributes" (SAML) as well."""
        group_sync("ssouser", user=self.user, response={"attributes": {"groups": ["neteng", "orgb_eng"]}})

        self.user.refresh_from_db()
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["neteng"])
        self.assertFalse(Group.objects.filter(name="orgb_eng").exists())

    def test_superuser_group_grants_flag_without_being_synced(self):
        """A superuser group omitted from SSO_SYNC_GROUPS still grants superuser, but is not created."""
        group_sync("ssouser", user=self.user, response={"groups": ["ops", "nautobot_admin"]})

        self.user.refresh_from_db()
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["ops"])
        self.assertTrue(self.user.is_superuser)
        self.assertFalse(Group.objects.filter(name="nautobot_admin").exists())

    def test_staff_group_grants_flag_without_being_synced(self):
        """A staff group omitted from SSO_SYNC_GROUPS still grants staff, but is not created."""
        group_sync("ssouser", user=self.user, response={"groups": ["ops", "nautobot_staff"]})

        self.user.refresh_from_db()
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["ops"])
        self.assertTrue(self.user.is_staff)
        self.assertFalse(Group.objects.filter(name="nautobot_staff").exists())

    def test_no_listed_groups_clears_memberships_but_keeps_flags(self):
        """A claim with nothing to sync clears memberships, while the flags still track the claim."""
        self.user.groups.add(Group.objects.create(name="ops"))

        group_sync("ssouser", user=self.user, response={"groups": ["orgb_eng", "nautobot_admin"]})

        self.user.refresh_from_db()
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), [])
        self.assertTrue(self.user.is_superuser)

    def test_omitted_groups_are_logged(self):
        """The groups that were not synced are named in the debug log."""
        with self.assertLogs("nautobot.extras.group_sync", level="DEBUG") as logs:
            group_sync("ssouser", user=self.user, response={"groups": ["ops", "orgb_eng"]})

        self.assertIn(
            "Not syncing groups omitted from SSO_SYNC_GROUPS for user ssouser: orgb_eng", "\n".join(logs.output)
        )
