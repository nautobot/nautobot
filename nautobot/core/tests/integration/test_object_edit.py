from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import LocationType
from nautobot.extras.models import Status
from nautobot.tenancy.models import Tenant


class ObjectEditTestCase(SeleniumTestCase):
    """Integration tests for object edit form."""

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

    def test_embedded_create(self):
        self.browser.visit(self.live_server_url)
        self.click_navbar_entry("Organization", "Locations")
        self.browser.find_by_id("add-button").click()

        # Click "Add a new tenant" button next to "Tenant" field
        form_xpath = "//form[@id='nb-create-form']"
        add_a_new_tenant_button_xpath = f"{form_xpath}//button[normalize-space()='Add a new tenant']"
        self.assertTrue(self.browser.is_element_present_by_xpath(add_a_new_tenant_button_xpath, wait_time=10))
        self.browser.find_by_xpath(add_a_new_tenant_button_xpath).click()

        # Assert that modal window with "Add a new tenant" form has been opened
        modal_xpath = "//div[@id='embedded_action_modal']"
        self.assertTrue(
            self.browser.is_element_present_by_xpath(
                f"{modal_xpath}//h2[normalize-space()='Add a new tenant']", wait_time=10
            )
        )

        # Fill the required "Name" input
        tenant_name = "test tenant"
        self.browser.find_by_xpath(f"{modal_xpath}//input[@name='name']").fill(tenant_name)

        # Press the "Create" (tenant) button
        self.browser.find_by_xpath(f"{modal_xpath}//button[@type='submit']").click()

        # Assert that newly created tenant record has been assigned to the related input from which it originated
        tenant_field_xpath = f"{form_xpath}//select[@name='tenant']"
        tenant_option_xpath = f"{tenant_field_xpath}/option[normalize-space()='{tenant_name}']"
        self.assertTrue(self.browser.is_element_present_by_xpath(tenant_option_xpath, wait_time=10))
        self.assertEqual(
            self.browser.find_by_xpath(tenant_field_xpath).value, self.browser.find_by_xpath(tenant_option_xpath).value
        )

        # Assert that successful object creation Django message has been displayed
        self.assertTrue(
            self.browser.is_element_present_by_xpath(
                f"//div[@id='header_messages']//div[contains(@class, 'alert alert-success') and normalize-space()='Created tenant {tenant_name}']",
                wait_time=10,
            )
        )

    def test_embedded_create_with_prefilled_content_type(self):
        self.browser.visit(self.live_server_url)
        self.click_navbar_entry("Organization", "Locations")
        self.browser.find_by_id("add-button").click()

        # Click "Add a new dynamic group" button next to "Dynamic groups" field
        add_a_new_dynamic_group_button_xpath = (
            "//form[@id='nb-create-form']//button[normalize-space()='Add a new dynamic group']"
        )
        self.assertTrue(self.browser.is_element_present_by_xpath(add_a_new_dynamic_group_button_xpath, wait_time=10))
        add_a_new_dynamic_group_button = self.browser.find_by_xpath(add_a_new_dynamic_group_button_xpath)
        self.scroll_element_into_view(element=add_a_new_dynamic_group_button)
        add_a_new_dynamic_group_button.click()

        # Assert that modal window with "Add a new dynamic group" form has been opened
        modal_xpath = "//div[@id='embedded_action_modal']"
        self.assertTrue(
            self.browser.is_element_present_by_xpath(
                f"{modal_xpath}//h2[normalize-space()='Add a new dynamic group']", wait_time=10
            )
        )

        # Assert that the "Content Type" field is pre-filled with "DCIM | location"
        content_type_field = self.browser.find_by_xpath(f"{modal_xpath}//select[@name='content_type']")
        self.assertEqual(content_type_field.value, "dcim.location")

    def test_embedded_search(self):
        tenant_name = "test tenant"
        Tenant.objects.create(name=tenant_name)

        self.browser.visit(self.live_server_url)
        self.click_navbar_entry("Organization", "Locations")
        self.browser.find_by_id("add-button").click()

        # Click "Search tenants" button next to "Tenant" field
        form_xpath = "//form[@id='nb-create-form']"
        search_tenants_button_xpath = f"{form_xpath}//button[normalize-space()='Search tenants']"
        self.assertTrue(self.browser.is_element_present_by_xpath(search_tenants_button_xpath, wait_time=10))
        self.browser.find_by_xpath(search_tenants_button_xpath).click()

        # Assert that modal window with "Search tenants" form has been opened
        modal_xpath = "//div[@id='embedded_action_modal']"
        self.assertTrue(
            self.browser.is_element_present_by_xpath(
                f"{modal_xpath}//h2[normalize-space()='Search tenants']", wait_time=10
            )
        )

        # Fill the "Name Contains" input
        self.browser.find_by_xpath(f"{modal_xpath}//input[@name='name__ic']").fill(tenant_name)

        # Press the "Search" (tenants) button
        self.browser.find_by_xpath(f"{modal_xpath}//button[@type='submit']").click()

        # Press the first (and only) row of search results
        first_row_xpath = f"{modal_xpath}//div[@class='nb-embedded-search-results']//tbody/tr"
        self.assertTrue(self.browser.is_element_present_by_xpath(first_row_xpath, wait_time=10))
        first_row = self.browser.find_by_xpath(first_row_xpath)
        self.scroll_element_into_view(element=first_row)
        self.browser.execute_script(
            "arguments[0].click();", first_row._element
        )  # Standard `.click()` does not work here

        # Assert that newly created tenant record has been assigned to the related input from which it originated
        tenant_field_xpath = f"{form_xpath}//select[@name='tenant']"
        tenant_option_xpath = f"{tenant_field_xpath}/option[normalize-space()='{tenant_name}']"
        self.assertTrue(self.browser.is_element_present_by_xpath(tenant_option_xpath, wait_time=20))
        self.assertEqual(
            self.browser.find_by_xpath(tenant_field_xpath).value, self.browser.find_by_xpath(tenant_option_xpath).value
        )

    def test_embedded_search_with_prefilled_content_type(self):
        self.browser.visit(self.live_server_url)
        self.click_navbar_entry("Organization", "Locations")
        self.browser.find_by_id("add-button").click()

        # Click "Search dynamic groups" button next to "Dynamic groups" field
        search_dynamic_groups_button_xpath = (
            "//form[@id='nb-create-form']//button[normalize-space()='Search dynamic groups']"
        )
        self.assertTrue(self.browser.is_element_present_by_xpath(search_dynamic_groups_button_xpath, wait_time=10))
        search_dynamic_groups_button = self.browser.find_by_xpath(search_dynamic_groups_button_xpath)
        self.scroll_element_into_view(element=search_dynamic_groups_button)
        search_dynamic_groups_button.click()

        # Assert that modal window with "Search dynamic groups" form has been opened
        modal_xpath = "//div[@id='embedded_action_modal']"
        self.assertTrue(
            self.browser.is_element_present_by_xpath(
                f"{modal_xpath}//h2[normalize-space()='Search dynamic groups']", wait_time=10
            )
        )

        # Assert that the "Content Type" field is pre-filled with "DCIM | location"
        content_type_field = self.browser.find_by_xpath(f"{modal_xpath}//select[@name='content_type']")
        self.assertEqual(content_type_field.value, "dcim.location")


class ObjectEditNestedEmbeddedCreateTestCase(SeleniumTestCase):
    """Integration tests for the embedded create modal that opens a second embedded create form."""

    form_xpath = "//form[@id='nb-create-form']"
    modal_xpath = "//div[@id='embedded_action_modal']"

    def setUp(self):
        super().setUp()
        self.login_as_superuser()

    def open_location_modal_from_device_form(self, device_name):
        self.browser.visit(f"{self.live_server_url}{reverse('dcim:device_add')}")
        self.browser.find_by_xpath(f"{self.form_xpath}//input[@name='name']").fill(device_name)
        self.click_modal_button(self.form_xpath, "Add a new location")
        self.wait_for_modal_title("Add a new location")

    def click_modal_button(self, scope_xpath, label):
        button_xpath = f"{scope_xpath}//button[normalize-space()='{label}']"
        self.assertTrue(self.browser.is_element_present_by_xpath(button_xpath, wait_time=10))
        button = self.browser.find_by_xpath(button_xpath)
        self.scroll_element_into_view(element=button)
        button.click()

    def wait_for_modal_title(self, title):
        self.assertTrue(
            self.browser.is_element_present_by_xpath(
                f"{self.modal_xpath}//h2[normalize-space()='{title}']", wait_time=10
            )
        )

    def fill_modal_name(self, name):
        self.browser.find_by_xpath(f"{self.modal_xpath}//input[@name='name']").fill(name)

    def submit_modal(self):
        self.browser.find_by_xpath(f"{self.modal_xpath}//button[@type='submit']").click()

    def modal_has_quick_add_button(self, label):
        return self.browser.is_element_present_by_xpath(
            f"{self.modal_xpath}//button[normalize-space()='{label}']", wait_time=1
        )

    def test_embedded_create_nested(self):
        device_name = "test device"
        location_type_name = "test location type"
        location_name = "test location"
        status = Status.objects.get(name="Active")
        self.open_location_modal_from_device_form(device_name)

        self.assertTrue(self.modal_has_quick_add_button("Add a new location type"))
        self.assertFalse(self.modal_has_quick_add_button("Add a new status"))
        self.assertFalse(self.modal_has_quick_add_button("Add a new tenant"))

        self.click_modal_button(self.modal_xpath, "Add a new location type")
        self.wait_for_modal_title("Add a new location type")
        self.assertFalse(self.modal_has_quick_add_button("Add a new location type"))
        self.assertFalse(self.modal_has_quick_add_button("Add a new status"))
        self.fill_modal_name(location_type_name)
        self.submit_modal()

        self.wait_for_modal_title("Add a new location")
        location_type_option_xpath = (
            f"{self.modal_xpath}//select[@name='location_type']/option[normalize-space()='{location_type_name}']"
        )
        self.assertTrue(self.browser.is_element_present_by_xpath(location_type_option_xpath, wait_time=10))
        self.assertEqual(
            self.browser.find_by_xpath(f"{self.modal_xpath}//select[@name='location_type']").value,
            self.browser.find_by_xpath(location_type_option_xpath).value,
        )

        self.fill_modal_name(location_name)
        self.browser.execute_script(
            "window.nb.select2.setSelect2Value("
            f"document.querySelector('#embedded_action_modal select[name=\"status\"]'), [{{text: 'Active', value: '{status.pk}'}}]);"
        )
        self.submit_modal()

        location_option_xpath = (
            f"{self.form_xpath}//select[@name='location']/option[normalize-space()='{location_name}']"
        )
        self.assertTrue(self.browser.is_element_present_by_xpath(location_option_xpath, wait_time=10))
        self.assertEqual(
            self.browser.find_by_xpath(f"{self.form_xpath}//select[@name='location']").value,
            self.browser.find_by_xpath(location_option_xpath).value,
        )
        self.assertEqual(self.browser.find_by_xpath(f"{self.form_xpath}//input[@name='name']").value, device_name)
        for created in (f"Created location type {location_type_name}", f"Created location {location_name}"):
            self.assertTrue(
                self.browser.is_element_present_by_xpath(
                    f"//div[@id='header_messages']//div[contains(@class, 'alert alert-success') and normalize-space()='{created}']",
                    wait_time=10,
                )
            )

    def test_embedded_create_nested_back_keeps_data(self):
        location_name = "test location"
        self.open_location_modal_from_device_form("test device")
        self.fill_modal_name(location_name)
        location_type_count = LocationType.objects.count()

        self.click_modal_button(self.modal_xpath, "Add a new location type")
        self.wait_for_modal_title("Add a new location type")
        self.click_modal_button(self.modal_xpath, "Back")

        self.wait_for_modal_title("Add a new location")
        self.assertEqual(self.browser.find_by_xpath(f"{self.modal_xpath}//input[@name='name']").value, location_name)
        self.assertEqual(LocationType.objects.count(), location_type_count)

    def test_embedded_create_nested_validation_error(self):
        location_name = "test location"
        existing_location_type = LocationType.objects.create(name="existing location type")
        self.open_location_modal_from_device_form("test device")
        self.fill_modal_name(location_name)

        self.click_modal_button(self.modal_xpath, "Add a new location type")
        self.wait_for_modal_title("Add a new location type")
        self.fill_modal_name(existing_location_type.name)
        self.submit_modal()

        self.assertTrue(
            self.browser.is_element_present_by_xpath(
                f"{self.modal_xpath}//li[contains(@class, 'text-danger')]",
                wait_time=10,
            )
        )
        self.click_modal_button(self.modal_xpath, "Back")

        self.wait_for_modal_title("Add a new location")
        self.assertEqual(self.browser.find_by_xpath(f"{self.modal_xpath}//input[@name='name']").value, location_name)
