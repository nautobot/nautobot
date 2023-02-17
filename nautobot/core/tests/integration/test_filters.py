from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.dcim import factory
from nautobot.dcim.models import Region, Site
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.models import CustomField
from nautobot.utilities.testing.integration import SeleniumTestCase


class ListViewFilterTestCase(SeleniumTestCase):
    """Integration test for the list view filter ui."""

    fixtures = ["user-data.json"]

    def setUp(self):
        super().setUp()
        self.login(self.user.username, self.password)
        factory.RegionFactory.create_batch(15, has_parent=False)
        factory.SiteFactory.create_batch(15, has_tenant=False)
        # set test user to admin
        self.user.is_superuser = True
        self.user.save()

        self.cf_text_field_name = "text_field"
        self.cf_integer_field_name = "integer_field"
        self.cf_select_field_name = "select_field"
        self.custom_fields = (
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, name=self.cf_text_field_name),
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_INTEGER, name=self.cf_integer_field_name),
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_SELECT, name=self.cf_select_field_name),
        )
        for custom_field in self.custom_fields:
            custom_field.content_types.set([ContentType.objects.get_for_model(Site)])

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_list_view_filter(self):
        """
        Test adding a filter with the list view filter modal and then
        removing the filter with the list view "filters" ui element.
        """

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

    def test_input_field_gets_updated(self):
        """Assert that a filter input field on Dynamic Filter Form updates if same field is updated."""
        self.browser.visit(f'{self.live_server_url}{reverse("dcim:site_list")}')
        # filter_btn = self.browser.find_by_id("id__filterbtn", wait_time=10)
        # default_filter_dom = self.browser.find_by_xpath("//div[@id='default-filter']")
        # advanced_filter_dom = self.browser.find_by_xpath("//div[@id='advanced-filter']")
        # advanced_tab_btn = self.browser.find_by_xpath("//a[@href='#advanced-filter']")
        # apply_filter_btn = default_filter_dom.find_by_xpath("//button[@type='submit']")
        # default_tab_btn = self.browser.find_by_xpath("//a[@href='#default-filter']")

        text_field_name = "cf_" + self.cf_text_field_name

        # Open the filter modal, configure filter and apply filter
        self.browser.find_by_id("id__filterbtn").click()
        self.browser.find_by_name(text_field_name).first.fill("test")
        self.browser.find_by_xpath("//div[@id='default-filter']//button[@type='submit']").click()

        # Assert on update of field in Default Filter the update is replicated on Advanced Filter
        self.browser.find_by_id("id__filterbtn").click()
        self.browser.find_by_name(text_field_name)[1].fill("test new")
        self.browser.find_by_xpath("//a[@href='#advanced-filter']").click()  # *
        cf_text_field_dom = self.browser.find_by_name(text_field_name)[2]
        self.assertEqual(cf_text_field_dom.value, "test new")

        # Assert on update of field in Advanced Filter the update is replicated on Default Filter
        self.browser.find_by_name(text_field_name)[2].fill("test new update")
        self.browser.find_by_xpath("//a[@href='#default-filter']").click()
        cf_text_field_dom = self.browser.find_by_name(text_field_name)[1]
        self.assertEqual(cf_text_field_dom.value, "test new update")

        # Assert on update of filter, the new filter is applied
        self.browser.find_by_xpath("//div[@id='default-filter']//button[@type='submit']").click()
        self.assertTrue(self.browser.is_text_present("test new update"))
