from django.urls import reverse
from selenium.webdriver.support.wait import WebDriverWait
from splinter.exceptions import ElementDoesNotExist

from nautobot.core.testing.integration import SeleniumTestCase


class BulkDeleteDeviceTestCase(SeleniumTestCase):
    """
    Test devices bulk delete.
    """

    def setUp(self):
        super().setUp()

        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        # Manufacturer
        self.click_navbar_entry("Devices", "Manufacturers")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:manufacturer_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:manufacturer_add"))
        self.browser.fill("name", "Test Manufacturer 1")
        self.click_edit_form_create_button()

        # Device Type
        self.click_navbar_entry("Devices", "Device Types")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:devicetype_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:devicetype_add"))
        self.fill_select2_field("manufacturer", "Test Manufacturer 1")
        self.browser.fill("model", "Test Device Type 1")
        self.click_edit_form_create_button()

        # LocationType
        self.click_navbar_entry("Organization", "Location Types")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:locationtype_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:locationtype_add"))
        self.fill_select2_multiselect_field("content_types", "dcim | device")
        self.browser.fill("name", "Test Location Type 1")
        self.click_edit_form_create_button()

        # Location 1
        self.click_navbar_entry("Organization", "Locations")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:location_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:location_add"))
        self.fill_select2_field("location_type", "Test Location Type 1")
        self.fill_select2_field("status", "")  # pick first status
        self.browser.fill("name", "Test Location 1")
        self.click_edit_form_create_button()

        # Location 2
        self.click_navbar_entry("Organization", "Locations")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:location_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:location_add"))
        self.fill_select2_field("location_type", "Test Location Type 1")
        self.fill_select2_field("status", "")  # pick first status
        self.browser.fill("name", "Test Location 2")
        self.click_edit_form_create_button()

        # Role
        self.click_navbar_entry("Organization", "Roles")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("extras:role_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("extras:role_add"))
        self.browser.fill("name", "Test Role 1")
        self.fill_select2_multiselect_field("content_types", "dcim | device")
        self.click_edit_form_create_button()

    def _create_device(self, name, location="Test Location 1"):
        self.click_navbar_entry("Devices", "Devices")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_add"))
        self.browser.fill("name", name)
        self.fill_select2_field("role", "Test Role 1")
        self.fill_select2_field("device_type", "Test Device Type 1")
        self.fill_select2_field("location", location)
        self.fill_select2_field("status", "")  # pick first status
        self.click_edit_form_create_button()

    def tearDown(self):
        # self.logout()
        super().tearDown()

    def _go_to_devices_list(self):
        self.click_navbar_entry("Devices", "Devices")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_list"))

    def _select_all(self):
        self.browser.find_by_xpath('//*[@id="object_list_form"]//input[@class="toggle"]').click()

    def _select_one(self):
        self.browser.find_by_xpath('//*[@id="object_list_form"]//input[@name="pk"]').click()

    def _click_delete_and_confirm(self):
        self.browser.find_by_xpath(
            '//*[@id="object_list_form"]//button[@type="submit"]/following-sibling::button[1]'
        ).click()
        self.browser.find_by_xpath('//*[@id="object_list_form"]//button[@name="_delete"]').click()
        self.browser.find_by_xpath('//button[@name="_confirm" and @type="submit"]').click()

    def _wait_for_job_results(self):
        end_statuses = ["Completed", "Failed"]
        WebDriverWait(self.browser, 30).until(
            lambda driver: driver.find_by_id("pending-result-label").text in end_statuses
        )

    def _verify_job_description(self, expected_job_description):
        job_description = self.browser.find_by_xpath('//td[text()="Job Description"]/following-sibling::td[1]').text
        self.assertEqual(job_description, expected_job_description)

    def _get_objects_table_count(self):
        objects_table_container = self.browser.find_by_xpath('//*[@id="object_list_form"]/div[1]/div')
        try:
            objects_table = objects_table_container.find_by_tag('tbody')
            return len(objects_table.find_by_tag('tr'))
        except ElementDoesNotExist:
            return 0

    def test_bulk_delete_require_selection(self):
        self._go_to_devices_list()

        # Click "delete selected" without selecting anything
        self.browser.find_by_xpath(
            '//*[@id="object_list_form"]//button[@type="submit"]/following-sibling::button[1]'
        ).click()
        self.browser.find_by_xpath('//*[@id="object_list_form"]//button[@name="_delete"]').click()

        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_list"))
        self.assertTrue(self.browser.is_text_present("No devices were selected for deletion.", wait_time=5))

    def test_bulk_delete_all_devices(self):
        # Create device for test
        self._create_device("Test Device Integration Test 1")
        self._create_device("Test Device Integration Test 2")
        self._go_to_devices_list()

        # Select all devices and delete them
        self._select_all()
        self._click_delete_and_confirm()

        # Verify job output
        self._verify_job_description("Bulk delete objects.")
        self._wait_for_job_results()

        job_status = self.browser.find_by_id("pending-result-label").text
        self.assertEqual(job_status, "Completed")

        self._go_to_devices_list()
        objects_count = self._get_objects_table_count()
        self.assertEqual(objects_count, 0)

    def test_bulk_delete_one_device(self):
        # Create device for test
        self._create_device("Test Device Integration Test 1")
        self._create_device("Test Device Integration Test 2")
        self._go_to_devices_list()

        # Select one device and delete it
        self._select_one()
        self._click_delete_and_confirm()

        # Verify job output
        self._verify_job_description("Bulk delete objects.")
        self._wait_for_job_results()

        job_status = self.browser.find_by_id("pending-result-label").text
        self.assertEqual(job_status, "Completed")

        self._go_to_devices_list()
        objects_count = self._get_objects_table_count()
        self.assertEqual(objects_count, 1)

    def test_bulk_delete_all_filtered_devices(self):
        # Create device for test
        self._create_device("Test Device Integration Test 1")
        self._create_device("Test Device Integration Test 2")
        self._create_device("Test Device Integration Test 3", location="Test Location 2")
        self._go_to_devices_list()

        # Filter devices
        self.browser.find_by_xpath('//*[@id="id__filterbtn"]').click()
        self.fill_filters_select2_field("location", "Test Location 2")
        self.browser.find_by_xpath('//*[@id="default-filter"]//button[@type="submit"]').click()

        # Select all devices and delete them
        self._select_all()
        self._click_delete_and_confirm()

        # Verify job output
        self._verify_job_description("Bulk delete objects.")
        self._wait_for_job_results()

        job_status = self.browser.find_by_id("pending-result-label").text
        self.assertEqual(job_status, "Completed")

        self._go_to_devices_list()
        objects_count = self._get_objects_table_count()
        self.assertEqual(objects_count, 2)

    def test_bulk_delete_one_filtered_devices(self):
        # Create device for test
        self._create_device("Test Device Integration Test 1")
        self._create_device("Test Device Integration Test 2")
        self._create_device("Test Device Integration Test 3", location="Test Location 2")
        self._create_device("Test Device Integration Test 4", location="Test Location 2")
        self._go_to_devices_list()

        # Filter devices
        self.browser.find_by_xpath('//*[@id="id__filterbtn"]').click()
        self.fill_filters_select2_field("location", "Test Location 2")
        self.browser.find_by_xpath('//*[@id="default-filter"]//button[@type="submit"]').click()

        # Select all devices and delete them
        self._select_one()
        self._click_delete_and_confirm()

        # Verify job output
        self._verify_job_description("Bulk delete objects.")
        self._wait_for_job_results()

        job_status = self.browser.find_by_id("pending-result-label").text
        self.assertEqual(job_status, "Completed")

        self._go_to_devices_list()
        objects_count = self._get_objects_table_count()
        self.assertEqual(objects_count, 3)
