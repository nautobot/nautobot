from django.urls import reverse

from nautobot.dcim import factory
from nautobot.dcim.models import Region
from nautobot.utilities.testing.integration import SeleniumTestCase


class ListViewFilterTestCase(SeleniumTestCase):
    """Integration test for the list view filter ui."""

    fixtures = ["user-data.json"]

    def setUp(self):
        super().setUp()
        self.login(self.user.username, self.password)
        factory.RegionFactory.create_batch(15, has_parent=False)
        factory.SiteFactory.create_batch(15, has_tenant=False)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_list_view_filter(self):
        """
        Test adding a filter with the list view filter modal and then
        removing the filter with the list view "filters" ui element.
        """
        # set test user to admin
        self.user.is_superuser = True
        self.user.save()

        # retrieve site list view
        self.browser.visit(f"{self.live_server_url}{reverse('dcim:site_list')}")
        filter_modal = self.browser.find_by_id("FilterForm_modal", wait_time=10)
        self.assertFalse(filter_modal.visible)

        # click on filter button to open the filter modal
        filter_button = self.browser.find_by_id("id__filterbtn", wait_time=10)
        filter_button.click()

        # assert the filter modal has appeared
        self.assertTrue(filter_modal.visible)

        # start typing a region into select2
        region = Region.objects.first()
        region_select = filter_modal.find_by_xpath(
            "//label[@for='id_region']/..//input[@class='select2-search__field']", wait_time=10
        )
        for _ in region_select.type(f"{region.name[:4]}", slowly=True):
            pass

        # click region option in select2
        region_option_xpath = f"//ul[@id='select2-id_region-results']//li[text()='{region.name}']"
        region_option = self.browser.find_by_xpath(region_option_xpath, wait_time=10)
        region_option.click()

        # click apply button in filter modal
        apply_button = filter_modal.find_by_xpath("//div[@id='default-filter']//button[@type='submit']", wait_time=10)
        apply_button.click()

        # assert the url has changed to add the filter param
        filtered_sites_url = self.browser.url
        self.assertIn("region=", filtered_sites_url)

        # find and click the remove all filter X button
        remove_all_filters = self.browser.find_by_xpath(
            "//div[@class='filters-applied']//span[@class='filter-selection']//span[@class='remove-filter-param']",
            wait_time=10,
        )
        remove_all_filters.click()

        # assert the filter param has been removed from the url
        self.assertNotIn("region=", self.browser.url)

        # navigate back to the filter page and try the individual filter remove X button
        self.browser.visit(filtered_sites_url)
        remove_single_filter = self.browser.find_by_xpath(
            "//div[@class='filters-applied']//span[@class='filter-selection']//span[@class='filter-selection-choice-remove remove-filter-param']",
            wait_time=10,
        )
        remove_single_filter.click()

        # assert the filter has been removed from the url
        self.assertNotIn("region=", self.browser.url)

        # assert the filter UI element is gone
        self.assertTrue(self.browser.is_element_not_present_by_xpath("//div[@class='filters-applied']"))
