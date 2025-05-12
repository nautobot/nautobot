from django.test import tag
from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase


class CreateDeviceTestCase(SeleniumTestCase):
    """
    Create a device and all pre-requisite objects through the UI.
    """

    @tag("fix_in_v3")
    def test_create_device(self):
        """
        This test goes through the process of creating a device in the UI. All pre-requisite objects are created:
        - Manufacturer
        - Device Type
        - LocationType
        - Location
        - Role
        - Device

        """
        self.login_as_superuser()

        # Manufacturer
        self.click_navbar_entry("Devices", "Manufacturers")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:manufacturer_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:manufacturer_add"))
        self.fill_input("name", "Test Manufacturer 1")
        self.click_edit_form_create_button()

        # Device Type
        self.click_navbar_entry("Devices", "Device Types")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:devicetype_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:devicetype_add"))
        self.fill_select2_field("manufacturer", "Test Manufacturer 1")
        self.fill_input("model", "Test Device Type 1")
        self.click_edit_form_create_button()

        # LocationType
        self.click_navbar_entry("Organization", "Location Types")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:locationtype_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:locationtype_add"))
        self.fill_select2_multiselect_field("content_types", "dcim | device")
        self.fill_input("name", "Test Location Type 1")
        self.click_edit_form_create_button()

        # Location
        self.click_navbar_entry("Organization", "Locations")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:location_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:location_add"))
        self.fill_select2_field("location_type", "Test Location Type 1")
        self.fill_select2_field("status", "")  # pick first status
        self.fill_input("name", "Test Location 1")
        self.click_edit_form_create_button()

        # Role
        self.click_navbar_entry("Organization", "Roles")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("extras:role_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("extras:role_add"))
        self.fill_input("name", "Test Role 1")
        self.fill_select2_multiselect_field("content_types", "dcim | device")
        self.click_edit_form_create_button()

        # Device
        self.click_navbar_entry("Devices", "Devices")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_add"))
        self.fill_input("name", "Test Device Integration Test 1")
        self.fill_select2_field("role", "Test Role 1")
        self.fill_select2_field("device_type", "Test Device Type 1")
        self.fill_select2_field("location", "Test Location 1")
        self.fill_select2_field("status", "")  # pick first status
        self.click_edit_form_create_button()

        # Assert that the device was created
        self.assertTrue(self.browser.is_text_present("Created device Test Device Integration Test 1", wait_time=5))
        self.assertTrue(self.browser.is_text_present("Test Location 1", wait_time=5))
        self.assertTrue(self.browser.is_text_present("Test Device Type 1", wait_time=5))
