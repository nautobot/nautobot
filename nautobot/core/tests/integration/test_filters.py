from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.factory import LocationFactory, LocationTypeFactory
from nautobot.dcim.models import Location, LocationType


class ListViewFilterTestCase(SeleniumTestCase):
    """Integration test for the list view filter ui."""

    fixtures = ["user-data.json"]

    def setUp(self):
        super().setUp()
        self.login(self.user.username, self.password)
        LocationTypeFactory.create_batch(7)
        print(LocationType.objects.all())
        LocationFactory.create_batch(10, has_tenant=True)
        print(Location.objects.all())

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

        # retrieve location list view
        self.browser.visit(f"{self.live_server_url}{reverse('dcim:location_list')}")
        filter_modal = self.browser.find_by_id("FilterForm_modal", wait_time=10)
        self.assertFalse(filter_modal.visible)

        # click on filter button to open the filter modal
        filter_button = self.browser.find_by_id("id__filterbtn", wait_time=10)
        filter_button.click()

        # assert the filter modal has appeared
        self.assertTrue(filter_modal.visible)

        # start typing a parent into select2
        location_type = LocationType.objects.filter(parent__isnull=True).first()
        parent = Location.objects.filter(location_type=location_type).first()
        parent_select = filter_modal.find_by_xpath(
            "//label[@for='id_parent']/..//input[@class='select2-search__field']", wait_time=10
        )
        for _ in parent_select.type(f"{parent.name[:4]}", slowly=True):
            pass

        # click parent option in select2
        parent_option_xpath = f"//ul[@id='select2-id_parent-results']//li[text()='{parent.name}']"
        parent_option = self.browser.find_by_xpath(parent_option_xpath, wait_time=10)
        parent_option.click()

        # click apply button in filter modal
        apply_button = filter_modal.find_by_xpath("//div[@id='default-filter']//button[@type='submit']", wait_time=10)
        apply_button.click()

        # assert the url has changed to add the filter param
        filtered_locations_url = self.browser.url
        self.assertIn("parent=", filtered_locations_url)

        # find and click the remove all filter X button
        remove_all_filters = self.browser.find_by_xpath(
            "//div[@class='filters-applied']//span[@class='filter-selection']//span[@class='remove-filter-param']",
            wait_time=10,
        )
        remove_all_filters.click()

        # assert the filter param has been removed from the url
        self.assertNotIn("parent=", self.browser.url)

        # navigate back to the filter page and try the individual filter remove X button
        self.browser.visit(filtered_locations_url)
        remove_single_filter = self.browser.find_by_xpath(
            "//div[@class='filters-applied']//span[@class='filter-selection']//span[@class='filter-selection-choice-remove remove-filter-param']",
            wait_time=10,
        )
        remove_single_filter.click()

        # assert the filter has been removed from the url
        self.assertNotIn("parent=", self.browser.url)

        # assert the filter UI element is gone
        self.assertTrue(self.browser.is_element_not_present_by_xpath("//div[@class='filters-applied']"))
