import netaddr

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.extras.models import Status
from nautobot.ipam.models import Prefix


class PrefixHierarchyTest(SeleniumTestCase):
    """
    This test case tests the indented Prefix hierarchy displayed in the Prefix list view.
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
        status = Status.objects.get_for_model(Prefix).first()
        Prefix(prefix=netaddr.IPNetwork("10.0.0.0/16"), status=status).validated_save()
        Prefix(prefix=netaddr.IPNetwork("10.0.0.0/24"), status=status).validated_save()

        # Navigate to Prefix list view
        self.browser.visit(self.live_server_url)
        # find_by_partial_text finds both Inventory > Provider Networks as well as the desired Networks top-level menu.
        self.browser.links.find_by_partial_text("Networks")[1].click()
        self.browser.links.find_by_partial_text("Prefixes").click()

        self.assertEqual(len(self.browser.find_by_tag("tr")[1].find_by_text("10.0.0.0/16")), 1)  # 10.0.0.0/16 is first
        self.assertEqual(len(self.browser.find_by_tag("tr")[2].find_by_text("10.0.0.0/24")), 1)  # 10.0.0.0/24 is second
        self.assertTrue(
            self.browser.find_by_tag("tr")[2].find_by_tag("i").first.has_class("mdi-circle-small")
        )  # 10.0.0.0/24 is indented via an <i> tag
