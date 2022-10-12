import netaddr

from django.test import override_settings

from nautobot.extras.models import Status
from nautobot.ipam.models import Prefix
from nautobot.utilities.testing.integration import SeleniumTestCase


class PrefixHierarchyTest(SeleniumTestCase):
    """
    This test case proves that the setting `DISABLE_PREFIX_LIST_HIERARCHY` causes the prefix list view to
    render a flat list when set to True, instead of calculating parent/child relationships, and that by
    default it is disabled.
    """

    def setUp(self):
        super().setUp()

        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_child_relationship_visible(self):
        """
        Test that 10.0.0.0/24 is shown under 10.0.0.0/16
        """
        status = Status.objects.get(slug="active")
        Prefix(prefix=netaddr.IPNetwork("10.0.0.0/16"), status=status).validated_save()
        Prefix(prefix=netaddr.IPNetwork("10.0.0.0/24"), status=status).validated_save()

        # Navigate to Prefix list view
        self.browser.visit(self.live_server_url)
        self.browser.links.find_by_partial_text("IPAM").click()
        self.browser.links.find_by_partial_text("Prefixes").click()

        self.assertEqual(len(self.browser.find_by_tag("tr")[1].find_by_text("10.0.0.0/16")), 1)  # 10.0.0.0/16 is first
        self.assertEqual(len(self.browser.find_by_tag("tr")[2].find_by_text("10.0.0.0/24")), 1)  # 10.0.0.0/24 is second
        self.assertTrue(
            self.browser.find_by_tag("tr")[2].find_by_tag("i").first.has_class("mdi-circle-small")
        )  # 10.0.0.0/24 is indented via an <i> tag

    @override_settings(DISABLE_PREFIX_LIST_HIERARCHY=True)
    def test_child_relationship_flat(self):
        """
        Test that 10.0.0.0/24 is NOT shown under 10.0.0.0/16, so the table is a flat list
        """
        status = Status.objects.get(slug="active")
        Prefix(prefix=netaddr.IPNetwork("10.0.0.0/16"), status=status).validated_save()
        Prefix(prefix=netaddr.IPNetwork("10.0.0.0/24"), status=status).validated_save()

        # Navigate to Prefix list view
        self.browser.visit(self.live_server_url)
        self.browser.links.find_by_partial_text("IPAM").click()
        self.browser.links.find_by_partial_text("Prefixes").click()

        self.assertEqual(len(self.browser.find_by_tag("tr")[1].find_by_text("10.0.0.0/16")), 1)  # 10.0.0.0/16 is first
        self.assertEqual(len(self.browser.find_by_tag("tr")[2].find_by_text("10.0.0.0/24")), 1)  # 10.0.0.0/24 is second
        self.assertEqual(
            len(self.browser.find_by_tag("tr")[2].find_by_tag("i")), 0
        )  # 10.0.0.0/24 is *not* indented via an <i> tag
