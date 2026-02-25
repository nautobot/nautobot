from django.test import override_settings
from django.urls import reverse
import netaddr

from nautobot.core.testing.integration import ObjectDetailsMixin, SeleniumTestCase
from nautobot.extras.models import Status
from nautobot.ipam.choices import PrefixTypeChoices
from nautobot.ipam.models import Namespace, Prefix


class PrefixHierarchyTest(SeleniumTestCase, ObjectDetailsMixin):
    """
    This test case tests the indented Prefix hierarchy displayed in the Prefix list view.
    """

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

        status = Status.objects.get_for_model(Prefix).first()
        self.namespace = Namespace.objects.create(name="Prefix Hierarchy Test test_child_relationship_visible")
        Prefix(
            prefix=netaddr.IPNetwork("10.0.0.0/16"),
            status=status,
            type=PrefixTypeChoices.TYPE_CONTAINER,
            namespace=self.namespace,
        ).validated_save()
        Prefix(
            prefix=netaddr.IPNetwork("10.0.0.0/24"),
            status=status,
            type=PrefixTypeChoices.TYPE_CONTAINER,
            namespace=self.namespace,
        ).validated_save()
        Prefix(
            prefix=netaddr.IPNetwork("10.0.0.0/30"),
            status=status,
            type=PrefixTypeChoices.TYPE_NETWORK,
            namespace=self.namespace,
        ).validated_save()

    def test_parent_child_relationship_visible_in_namespace_detail_view(self):
        """
        Test the rendering in the Namespace "Prefixes" sub-tab.
        """
        # Navigate to Namespace Prefixes detail view tab
        self.browser.visit(self.live_server_url)
        self.click_navbar_entry("IPAM", "Namespaces")
        self.browser.links.find_by_text(self.namespace.name).click()
        self.switch_tab("Prefixes")

        # 10.0.0.0/16 is first...
        self.assertEqual(self.browser.find_by_tag("tr")[1].find_by_tag("a").first.text, "10.0.0.0/16")
        # 10.0.0.0/24 is second...
        self.assertEqual(self.browser.find_by_tag("tr")[2].find_by_tag("a").first.text, "10.0.0.0/24")
        # ...and it is indented appropriately as a subtree element
        self.assertTrue(
            self.browser.find_by_tag("tr")[2].find_by_tag("span").first.has_class("nb-subtree-next-sibling")
        )
        # 10.0.0.0/30 is third...
        self.assertEqual(self.browser.find_by_tag("tr")[3].find_by_tag("a").first.text, "10.0.0.0/30")
        # ...and it is indented appropriately as a subtree element
        self.assertTrue(
            self.browser.find_by_tag("tr")[3].find_by_tag("span")[0].has_class("nb-subtree-ancestor-next-sibling")
        )
        self.assertTrue(self.browser.find_by_tag("tr")[3].find_by_tag("span")[1].has_class("nb-subtree-next-sibling"))

    def test_parent_child_relationship_navigable_in_list_view(self):
        self.browser.visit(
            f"{self.live_server_url}{reverse('ipam:prefix_list')}?namespace={self.namespace.pk}&max_depth=1"
        )

        self.assertEqual(len(self.browser.find_by_tag("tr")), 2)  # header + 1 prefix
        # 10.0.0.0/16 is first...
        self.assertEqual(self.browser.find_by_tag("tr")[1].find_by_tag("a").first.text, "10.0.0.0/16")
        # ...and it has an expandable caret
        self.assertTrue(
            self.browser.find_by_tag("tr")[1].find_by_tag("button").first.has_class("nb-subtree-expandable")
        )
        self.browser.find_by_tag("tr")[1].find_by_tag("button").first.click()
        self.assertTrue(self.browser.find_by_tag("tr")[1].find_by_tag("button").first.has_class("nb-subtree-expanded"))
        self.assertEqual(len(self.browser.find_by_tag("tr")), 3)  # header + 2 prefixes

        # 10.0.0.0/24 is second...
        self.assertEqual(self.browser.find_by_tag("tr")[2].find_by_tag("a").first.text, "10.0.0.0/24")
        # ...and it is indented appropriately as a subtree element
        self.assertTrue(
            self.browser.find_by_tag("tr")[2].find_by_tag("span").first.has_class("nb-subtree-next-sibling")
        )
        # ...and it has an expandable caret
        self.assertTrue(
            self.browser.find_by_tag("tr")[2].find_by_tag("button").first.has_class("nb-subtree-expandable")
        )
        self.browser.find_by_tag("tr")[2].find_by_tag("button").first.click()
        self.assertTrue(self.browser.find_by_tag("tr")[2].find_by_tag("button").first.has_class("nb-subtree-expanded"))
        self.assertEqual(len(self.browser.find_by_tag("tr")), 4)  # header + 3 prefixes

        # 10.0.0.0/30 is third...
        self.assertEqual(self.browser.find_by_tag("tr")[3].find_by_tag("a").first.text, "10.0.0.0/30")
        # ...and it is indented appropriately as a subtree element
        self.assertTrue(
            self.browser.find_by_tag("tr")[3].find_by_tag("span")[0].has_class("nb-subtree-ancestor-next-sibling")
        )
        self.assertTrue(self.browser.find_by_tag("tr")[3].find_by_tag("span")[1].has_class("nb-subtree-next-sibling"))
        # ...and it does NOT have an expandable caret
        self.assertTrue(self.browser.find_by_tag("tr")[3].find_by_tag("span")[2].has_class("nb-subtree"))
        self.assertFalse(self.browser.find_by_tag("tr")[3].find_by_tag("span")[2].has_class("nb-subtree-expandable"))

    @override_settings(PREFIX_LIST_DEFAULT_MAX_DEPTH=1, MAX_PAGE_SIZE=100)
    def test_banner_rendering(self):
        # First, confirm that DEFAULT_MAX_DEPTH message is displayed exactly once
        self.browser.visit(f"{self.live_server_url}{reverse('ipam:prefix_list')}?namespace={self.namespace.pk}")

        self.assertEqual(len(self.browser.find_by_tag("tr")), 2)  # header plus one root prefix
        self.assertEqual(
            len(self.browser.find_by_css("#header_messages .alert")),
            1,
            [elem.value for elem in self.browser.find_by_css("#header_messages .alert")],
        )

        alert = self.browser.find_by_css("#header_messages .alert").first
        self.assertEqual(
            alert.value,
            "This table has been filtered by default due to the configured PREFIX_LIST_DEFAULT_MAX_DEPTH setting.",
        )

        # Next, select "per_page=1000" from the paginator and verify an additional alert is added
        self.browser.find_by_id("per_page").first.click()
        self.browser.find_by_value("1000").last.click()

        self.assertEqual(
            len(self.browser.find_by_css("#header_messages .alert")),
            2,
            [elem.value for elem in self.browser.find_by_css("#header_messages .alert")],
        )

        alert = self.browser.find_by_css("#header_messages .alert-info").first
        self.assertEqual(
            alert.value,
            "This table has been filtered by default due to the configured PREFIX_LIST_DEFAULT_MAX_DEPTH setting.",
        )
        alert = self.browser.find_by_css("#header_messages .alert-warning").first
        self.assertEqual(
            alert.value,
            'Requested "per_page" is too large. No more than 100 items may be displayed at a time.',
        )

        # Next, refresh the page and make sure the two alerts are still rendered
        self.browser.reload()

        self.assertEqual(
            len(self.browser.find_by_css("#header_messages .alert")),
            2,
            [elem.value for elem in self.browser.find_by_css("#header_messages .alert")],
        )

        alert = self.browser.find_by_css("#header_messages .alert-info").first
        self.assertEqual(
            alert.value,
            "This table has been filtered by default due to the configured PREFIX_LIST_DEFAULT_MAX_DEPTH setting.",
        )
        alert = self.browser.find_by_css("#header_messages .alert-warning").first
        self.assertEqual(
            alert.value,
            'Requested "per_page" is too large. No more than 100 items may be displayed at a time.',
        )

        # Next, select "per_page=25" from the paginator and verify the additional alert is removed
        self.browser.find_by_id("per_page").first.click()
        self.browser.find_by_value("25").last.click()

        self.assertEqual(
            len(self.browser.find_by_css("#header_messages .alert")),
            1,
            [elem.value for elem in self.browser.find_by_css("#header_messages .alert")],
        )

        alert = self.browser.find_by_css("#header_messages .alert").first
        self.assertEqual(
            alert.value,
            "This table has been filtered by default due to the configured PREFIX_LIST_DEFAULT_MAX_DEPTH setting.",
        )
