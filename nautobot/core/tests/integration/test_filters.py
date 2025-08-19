from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.factory import LocationTypeFactory
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.models import CustomField, CustomFieldChoice, Status, Tag


class ListViewFilterTestCase(SeleniumTestCase):
    """Integration test for the list view filter ui."""

    def setUp(self):
        super().setUp()
        self.login(self.user.username, self.password)
        if not LocationType.objects.filter(name="Campus").exists():
            LocationTypeFactory.create_batch(7)
        lt1 = LocationType.objects.get(name="Campus")
        lt2 = LocationType.objects.get(name="Root")
        lt3 = LocationType.objects.get(name="Building")
        lt4 = LocationType.objects.get(name="Floor")
        location_status = Status.objects.get_for_model(Location).first()
        campus_loc = Location.objects.create(name="Filter Test Location 1", location_type=lt1, status=location_status)
        Location.objects.create(name="Filter Test Location 2", location_type=lt2, status=location_status)
        building_loc = Location.objects.create(
            name="Filter Test Location 3", location_type=lt3, parent=campus_loc, status=location_status
        )
        Location.objects.create(
            name="Filter Test Location 4", location_type=lt4, parent=building_loc, status=location_status
        )
        Location.objects.create(
            name="Filter Test Location 5", location_type=lt4, parent=building_loc, status=location_status
        )
        # set test user to admin
        self.user.is_superuser = True
        self.user.save()

        self.cf_text_field_label = "Text Field"
        self.cf_integer_field_label = "Integer Field"
        self.cf_select_field_label = "Select Field"
        self.cf_multi_select_field_label = "Multi Select Field"
        self.custom_fields = (
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, label=self.cf_text_field_label),
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_INTEGER, label=self.cf_integer_field_label),
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_SELECT, label=self.cf_select_field_label),
            CustomField.objects.create(
                type=CustomFieldTypeChoices.TYPE_MULTISELECT, label=self.cf_multi_select_field_label
            ),
        )
        for custom_field in self.custom_fields:
            custom_field.content_types.set([ContentType.objects.get_for_model(Location)])

        for x in ["A", "B", "C"]:
            CustomFieldChoice.objects.create(custom_field=self.custom_fields[2], value=f"SingleSelect Option {x}")
            CustomFieldChoice.objects.create(custom_field=self.custom_fields[3], value=f"MultiSelect Option {x}")

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_list_view_filter(self):
        """
        Test adding a filter with the list view filter modal and then
        removing the filter with the list view "filters" ui element.
        """

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
            "//div[@class='filters-applied']//span[@class='filter-selection']//"
            "span[@class='filter-selection-choice-remove remove-filter-param']",
            wait_time=10,
        )
        remove_single_filter.click()

        # assert the filter has been removed from the url
        self.assertNotIn("parent=", self.browser.url)

        # assert the filter UI element is gone
        self.assertTrue(self.browser.is_element_not_present_by_xpath("//div[@class='filters-applied']"))

    def change_field_value(self, field_name, value, field_type="input", idx=0, select2_field_name=None):
        """Change the value of an input or select field.

        Args:
            field_name (str): The name of the input or select field.
            value (str or int): The value to fill in the input field or select from the select field.
            field_type (str, optional): The type of the field, either "input" or "select".
            idx (int, optional): The index of the field in case there are multiple fields with the same name.
            select2_field_name (str, optional): The name of the select2 field in case it is different from the
                input field name.
        """
        if field_type == "input":
            self.browser.find_by_name(field_name)[idx].fill(value)
        else:
            self.browser.find_by_xpath(f"//select[@name='{field_name}']//following-sibling::span")[idx].click()
            select2_field_name = select2_field_name or field_name
            select_field_xpath = (
                f"//ul[@id='select2-id_{select2_field_name}-results']/li[contains(@class,"
                f"'select2-results__option')  and contains(text(),'{value}')]"
            )
            self.browser.find_by_xpath(select_field_xpath).click()

    def test_input_field_gets_updated(self):
        """Assert that a filter input/select field on Dynamic Filter Form updates if same field is updated."""
        self.browser.visit(f"{self.live_server_url}{reverse('dcim:location_list')}")

        text_field_name = self.custom_fields[0].add_prefix_to_cf_key()
        integer_field_name = self.custom_fields[1].add_prefix_to_cf_key()
        select_field_name = self.custom_fields[2].add_prefix_to_cf_key()
        multi_select_field_name = self.custom_fields[3].add_prefix_to_cf_key()
        apply_btn_xpath = "//div[@id='default-filter']//button[@type='submit']"

        # Open the filter modal, configure filter and apply filter
        self.browser.find_by_id("id__filterbtn").click()
        self.change_field_value(text_field_name, "example-text")
        self.change_field_value(integer_field_name, 4356)
        self.change_field_value(select_field_name, "SingleSelect Option A", field_type="select")
        self.change_field_value(multi_select_field_name, "MultiSelect Option A", field_type="select")
        self.browser.find_by_xpath(apply_btn_xpath).click()  # Click on apply filter button
        self.assertTrue(self.browser.is_text_present("example-text"))
        self.assertTrue(self.browser.is_text_present("4356"))
        self.assertTrue(self.browser.is_text_present("SingleSelect Option A"))
        self.assertTrue(self.browser.is_text_present("MultiSelect Option A"))

        # Assert on update of field in Default Filter the update is replicated on Advanced Filter
        self.browser.find_by_id("id__filterbtn").click()
        self.change_field_value(text_field_name, "test new", idx=1)
        self.change_field_value(integer_field_name, 1111, idx=1)
        self.change_field_value(select_field_name, "SingleSelect Option B", field_type="select")
        self.change_field_value(multi_select_field_name, "MultiSelect Option B", field_type="select")
        self.browser.find_by_xpath("//a[@href='#advanced-filter']").click()
        self.assertEqual(self.browser.find_by_name(text_field_name)[2].value, "test new")
        self.assertEqual(self.browser.find_by_name(integer_field_name)[2].value, "1111")
        # CustomSelect Field is a MultiValueCharField, and the only way to get its values is using this approach.
        # Its values are the  options available on the select field
        custom_select_field = self.browser.find_by_name(select_field_name)[2].find_by_tag("option")
        self.assertEqual(custom_select_field[0].value, "SingleSelect Option A")
        self.assertEqual(custom_select_field[1].value, "SingleSelect Option B")
        custom_multi_select_field = self.browser.find_by_name(multi_select_field_name)[2].find_by_tag("option")
        self.assertEqual(custom_multi_select_field[0].value, "MultiSelect Option A")
        self.assertEqual(custom_multi_select_field[1].value, "MultiSelect Option B")

        # Assert on update of field in Advanced Filter the update is replicated on Default Filter
        self.change_field_value(text_field_name, "test new update", idx=2)
        self.change_field_value(integer_field_name, 8888, idx=2)
        self.change_field_value(
            select_field_name,
            "SingleSelect Option C",
            field_type="select",
            idx=1,
            select2_field_name="form-2-lookup_value",
        )
        self.change_field_value(
            multi_select_field_name,
            "MultiSelect Option C",
            field_type="select",
            idx=1,
            select2_field_name="form-1-lookup_value",
        )
        self.browser.find_by_xpath("//a[@href='#default-filter']").click()
        self.assertEqual(self.browser.find_by_name(text_field_name)[1].value, "test new update")
        self.assertEqual(self.browser.find_by_name(integer_field_name)[1].value, "8888")
        custom_select_values = self.browser.find_by_name(select_field_name)[1].find_by_tag("option")
        self.assertEqual(custom_select_values[0].value, "SingleSelect Option A")
        self.assertEqual(custom_select_values[1].value, "SingleSelect Option B")
        self.assertEqual(custom_select_values[2].value, "SingleSelect Option C")
        multi_custom_select_values = self.browser.find_by_name(multi_select_field_name)[1].find_by_tag("option")
        self.assertEqual(multi_custom_select_values[0].value, "MultiSelect Option A")
        self.assertEqual(multi_custom_select_values[1].value, "MultiSelect Option B")
        self.assertEqual(multi_custom_select_values[2].value, "MultiSelect Option C")

        # Assert on update of filter, the new filter is applied
        self.browser.find_by_xpath(apply_btn_xpath).click()  # Click on apply filter button
        self.assertTrue(self.browser.is_text_present("test new update"))
        self.assertTrue(self.browser.is_text_present("8888"))
        self.assertTrue(self.browser.is_text_present("SingleSelect Option C"))
        self.assertTrue(self.browser.is_text_present("MultiSelect Option C"))

    def test_advanced_filter_application(self):
        """Assert that filters are applied successfully when using the advanced filter."""
        # Go to the location list view
        self.browser.visit(f"{self.live_server_url}{reverse('dcim:location_list')}")
        # create a new tag
        tag = Tag.objects.create(name="Tag1")
        tag.content_types.set([ContentType.objects.get_for_model(Location)])

        # Open the filter modal
        self.browser.find_by_id("id__filterbtn").click()
        # Go to advanced Tab
        self.browser.find_by_xpath("//a[@href='#advanced-filter']").click()

        # Click on the first column lookup field and select Tags
        self.browser.find_by_id("select2-id_form-0-lookup_field-container").click()
        self.browser.find_by_xpath(
            "//ul[@id='select2-id_form-0-lookup_field-results']/li[contains(@class,'select2-results__option') "
            "and contains(text(),'Tags')]"
        ).click()

        # Click on the second column lookup type and select exact
        self.browser.find_by_id("select2-id_form-0-lookup_type-container").click()
        self.browser.find_by_xpath(
            "//ul[@id='select2-id_form-0-lookup_type-results']/li[contains(@class,'select2-results__option') "
            "and contains(text(),'exact')]"
        ).click()
        # find the input field for the tag
        container = self.browser.find_by_xpath(
            "//span[@class='select2 select2-container select2-container--bootstrap select2-container--below']"
        )
        container.click()
        # select tag
        self.browser.find_by_xpath(
            "//span[@class='select2-results']//ul[@class='select2-results__options']/li[contains(@class,'select2-results__option') "
            f"and contains(text(),{tag.name})]"
        ).click()

        apply_btn_xpath = "//div[@id='advanced-filter']//button[@type='submit']"
        self.browser.find_by_xpath(apply_btn_xpath).click()
        filter_modal = self.browser.find_by_id("FilterForm_modal", wait_time=10)
        # Model disappears
        self.assertFalse(filter_modal.visible)
        # Assert the choice is applied
        self.browser.find_by_xpath(f"//li[@class='filter-selection-choice' and contains(text(),{tag.name})]")
