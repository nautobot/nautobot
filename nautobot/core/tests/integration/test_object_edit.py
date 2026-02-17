from nautobot.core.testing.integration import SeleniumTestCase


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
        self.browser.find_by_xpath(f"{form_xpath}//button[normalize-space()='Add a new tenant']").click()

        # Assert that modal window with "Add a new tenant" form has been opened
        modal_xpath = "//div[@id='embedded_action_modal']"
        self.assertTrue(
            self.browser.is_element_present_by_xpath(
                f"{modal_xpath}//h4[normalize-space()='Add a new tenant']", wait_time=10
            )
        )

        # Fill the required "Name" input
        tenant_name = "test tenant"
        self.browser.find_by_xpath(f"{modal_xpath}//input[@name='name']").fill(tenant_name)

        # Press the "Create" (tenant) button
        create_button = self.browser.find_by_xpath(f"{modal_xpath}//button[@type='submit']")
        self.scroll_element_into_view(element=create_button)
        create_button.click()

        # Assert that newly created tenant record has been assigned to the related input from which it originated
        tenant_field_xpath = f"{form_xpath}//select[@name='tenant']"
        tenant_field = self.browser.find_by_xpath(tenant_field_xpath)
        self.assertEqual(
            self.browser.find_by_xpath(
                f"{tenant_field_xpath}/option[@value='{tenant_field.value}']", wait_time=10
            ).text,
            tenant_name,
        )
