import netaddr

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings

from nautobot.extras.models import Status
from nautobot.ipam.models import Prefix
from nautobot.utilities.testing.integration import SplinterTestCase


class PrefixHierarchyTest(SplinterTestCase):
    """
    This test case proves that the `DISABLE_PREFIX_LIST_HIERARCHY` causes the prefix list view to render a flast list
    when set to True, instead of calculating parent/child relationships, and that by default it is disabled.
    """

    def setUp(self):
        super().setUp()

        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        status = Status.objects.create(name="foo", slug="foo")
        status.content_types.add(ContentType.objects.get_for_model(Prefix))

        Prefix.objects.create(prefix=netaddr.IPNetwork("10.0.0.0/16"), status=status)
        Prefix.objects.create(prefix=netaddr.IPNetwork("10.0.0.0/24"), status=status)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_child_relationship_visible(self):
        """
        Test that 10.0.0.0/24 is shown under 10.0.0.0/16
        """
        # Navigate to Prefix list view
        self.browser.visit(self.live_server_url)
        self.browser.links.find_by_partial_text("IPAM").click()
        self.browser.links.find_by_partial_text("Prefixes").click()

        breakpoint()

        self.assertTrue(self.browser.is_element_present_by_css(".mdi-circle-small"))

    #@override_settings(DISABLE_PREFIX_LIST_HIERARCHY=True)
    def test_child_relationship_flat(self):
        """
        Test that 10.0.0.0/24 is NOT shown under 10.0.0.0/16 asn is just a flat list
        """
        # Navigate to Prefix list view
        self.browser.visit(self.live_server_url)
        self.browser.links.find_by_partial_text("IPAM").click()
        self.browser.links.find_by_partial_text("Prefixes").click()

        self.assertTrue(self.browser.is_element_not_present_by_css(".mdi-circle-small"))
