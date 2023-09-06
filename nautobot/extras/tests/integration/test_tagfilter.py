import time

from django.contrib.contenttypes.models import ContentType

from nautobot.circuits.models import Provider
from nautobot.extras.models import Tag
from nautobot.core.testing.integration import SeleniumTestCase


class TagFilterTestCase(SeleniumTestCase):
    """
    Integration test to check behavior of TagFilter in the UI after https://github.com/nautobot/nautobot/issues/4216.
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        # Dynamic model dropdowns like TagFilter default to 50 items at a time from the API
        provider_ct = ContentType.objects.get_for_model(Provider)
        for i in range(1, 52):
            self.tag = Tag.objects.create(name=f"A Provider Tag {i:02d}")
            self.tag.content_types.add(provider_ct)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_tag_matching_content_type(self):
        # Navigate to the Provider list view
        self.browser.links.find_by_partial_text("Circuits").click()
        self.browser.links.find_by_partial_text("Providers").click()

        # Open the filter form
        self.browser.find_by_id("id__filterbtn").click()
        time.sleep(0.5)

        # Find the "Tags" field and select it
        self.browser.find_by_xpath("//label[@for='id_tags']").click()
        self.browser.driver.switch_to.active_element.click()
        # Wait for choices to load
        time.sleep(0.5)
        # Each of first 50 tags should appear in the dropdown
        for i in range(1, 51):
            self.assertTrue(self.browser.is_text_present(f"A Provider Tag {i:02d}"))
        self.assertFalse(self.browser.is_text_present("A Provider Tag 51"))

    def test_tag_not_matching_content_type(self):
        # Navigate to the Location list view
        self.browser.links.find_by_partial_text("Organization").click()
        self.browser.links.find_by_partial_text("Locations").click()

        # Open the filter form
        self.browser.find_by_id("id__filterbtn").click()
        time.sleep(0.5)

        # Find the "Tags" field and select it
        self.browser.find_by_xpath("//label[@for='id_tags']").click()
        self.browser.driver.switch_to.active_element.click()
        # Wait for choices to load
        time.sleep(0.5)
        # Tags should not appear in the dropdown since they don't apply to Locations
        self.assertFalse(self.browser.is_text_present("A Provider Tag"))
