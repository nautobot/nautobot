from django.urls import reverse
from selenium.webdriver.common.keys import Keys

from nautobot.core.testing.integration import SeleniumTestCase


class CreateDeviceTestCase(SeleniumTestCase):
    """
    Create a device and all pre-requisite objects through the UI.
    """

    def _click_nav_bar(self, parent_menu_name, child_menu_name):
        """
        Helper function to click on a parent menu and child menu in the navigation bar.
        """

        parent_menu_xpath = f"//*[@id='navbar']//a[@class='dropdown-toggle' and normalize-space()='{parent_menu_name}']"
        parent_menu = self.browser.find_by_xpath(parent_menu_xpath, wait_time=5)
        if not parent_menu["aria-expanded"] == "true":
            parent_menu.click()
        child_menu_xpath = f"{parent_menu_xpath}/following-sibling::ul//li[.//a[normalize-space()='{child_menu_name}']]"
        child_menu = self.browser.find_by_xpath(child_menu_xpath, wait_time=5)
        child_menu.click()

        # Wait for body element to appear
        self.assertTrue(self.browser.is_element_present_by_tag("body", wait_time=5), "Page failed to load")

    def _click_add_button(self):
        """
        Helper function to click the "Add" button on a list view.
        """
        add_button = self.browser.find_by_xpath("//a[@id='add-button']", wait_time=5)
        add_button.click()

        # Wait for body element to appear
        self.assertTrue(self.browser.is_element_present_by_tag("body", wait_time=5), "Page failed to load")

    def _click_create_button(self):
        """
        Helper function to click the "Create" button on a form.
        """
        add_button = self.browser.find_by_xpath("//button[@name='_create']", wait_time=5)
        add_button.click()

        # Wait for body element to appear
        self.assertTrue(self.browser.is_element_present_by_tag("body", wait_time=5), "Page failed to load")

    def _fill_select2_field(self, field_name, value):
        """
        Helper function to fill a Select2 single selection field.
        """
        self.browser.find_by_xpath(f"//select[@id='id_{field_name}']//following-sibling::span").click()
        search_box = self.browser.find_by_xpath(
            "//*[@class='select2-search select2-search--dropdown']//input", wait_time=5
        )
        for _ in search_box.first.type(value, slowly=True):
            pass

        # wait for "searching" to disappear
        self.browser.is_element_not_present_by_css(".loading-results", wait_time=5)
        search_box.first.type(Keys.ENTER)

    def _fill_select2_multiselect_field(self, field_name, value):
        """
        Helper function to fill a Select2 multi-selection field.
        """
        search_box = self.browser.find_by_xpath(f"//select[@id='id_{field_name}']//following-sibling::span//input")
        for _ in search_box.first.type(value, slowly=True):
            pass

        # wait for "searching" to disappear
        self.browser.is_element_not_present_by_css(".loading-results", wait_time=5)
        search_box.first.type(Keys.ENTER)

    def test_create_device(self):
        """
        This test goes through the process of creating a device in the UI. All pre-requisite objects are created:
        - Manufacturer
        - Device Type
        - LocationType
        - Location
        - Device

        """
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        # Manufacturer
        self._click_nav_bar("Devices", "Manufacturers")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:manufacturer_list"))
        self._click_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:manufacturer_add"))
        self.browser.fill("name", "Test Manufacturer 1")
        self._click_create_button()

        # Device Type
        self._click_nav_bar("Devices", "Device Types")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:devicetype_list"))
        self._click_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:devicetype_add"))
        self._fill_select2_field("manufacturer", "Test Manufacturer 1")
        self.browser.fill("model", "Test Device Type 1")
        self._click_create_button()

        # LocationType
        self._click_nav_bar("Organization", "Location Types")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:locationtype_list"))
        self._click_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:locationtype_add"))
        self._fill_select2_multiselect_field("content_types", "dcim | device")
        self.browser.fill("name", "Test Location Type 1")
        self._click_create_button()

        # Location
        self._click_nav_bar("Organization", "Locations")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:location_list"))
        self._click_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:location_add"))
        self._fill_select2_field("location_type", "Test Location Type 1")
        self._fill_select2_field("status", "")  # pick first status
        self.browser.fill("name", "Test Location 1")
        self._click_create_button()

        # Device
        self._click_nav_bar("Devices", "Devices")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_list"))
        self._click_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_add"))
        self.browser.fill("name", "Test Device Integration Test 1")
        self._fill_select2_field("role", "")  # pick first role
        self._fill_select2_field("device_type", "Test Device Type 1")
        self._fill_select2_field("location", "Test Location 1")
        self._fill_select2_field("status", "")  # pick first status
        self._click_create_button()

        # Assert that the device was created
        self.assertTrue(self.browser.is_text_present("Created device Test Device Integration Test 1", wait_time=5))
        self.assertTrue(self.browser.is_text_present("Test Location 1", wait_time=5))
        self.assertTrue(self.browser.is_text_present("Test Device Type 1", wait_time=5))
