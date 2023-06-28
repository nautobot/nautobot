import netaddr

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.extras.models import Status
from nautobot.ipam.choices import PrefixTypeChoices
from nautobot.ipam.models import Namespace, Prefix


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
        namespace = Namespace.objects.create(name="Prefix Hierarchy Test test_child_relationship_visible")
        Prefix(
            prefix=netaddr.IPNetwork("10.0.0.0/16"),
            status=status,
            type=PrefixTypeChoices.TYPE_CONTAINER,
            namespace=namespace,
        ).validated_save()
        Prefix(
            prefix=netaddr.IPNetwork("10.0.0.0/24"),
            status=status,
            type=PrefixTypeChoices.TYPE_NETWORK,
            namespace=namespace,
        ).validated_save()

        # Navigate to Namespace Prefixes list view
        self.browser.visit(self.live_server_url)
        self.browser.links.find_by_partial_text("IPAM").click()
        self.browser.links.find_by_partial_text("Namespaces").click()
        self.browser.links.find_by_text(namespace.name).click()
        self.browser.find_by_xpath("//ul[@id='tabs']//a[contains(., 'Prefixes')]").click()

        self.assertEqual(len(self.browser.find_by_tag("tr")[1].find_by_text("10.0.0.0/16")), 1)  # 10.0.0.0/16 is first
        self.assertEqual(len(self.browser.find_by_tag("tr")[2].find_by_text("10.0.0.0/24")), 1)  # 10.0.0.0/24 is second
        self.assertTrue(
            self.browser.find_by_tag("tr")[2].find_by_tag("i").first.has_class("mdi-circle-small")
        )  # 10.0.0.0/24 is indented via an <i> tag
