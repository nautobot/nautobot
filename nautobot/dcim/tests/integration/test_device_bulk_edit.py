import uuid

from django.urls import reverse

from nautobot.core.testing.integration import BulkOperationsMixin, ObjectsListMixin, SeleniumTestCase
from nautobot.dcim.models import Device
from nautobot.extras.tests.integration import create_test_device


class BulkEditDeviceTestCase(SeleniumTestCase, ObjectsListMixin, BulkOperationsMixin):
    """
    Test devices bulk delete.
    """

    def setUp(self):
        super().setUp()

        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        self.run_uuid = str(uuid.uuid4())

        self._create_device("Test Device Integration Test 1")
        self._create_device("Test Device Integration Test 2")
        self._create_device("Test Device Integration Test 3", location="Test Location 2")
        self._create_device("Test Device Integration Test 4", location="Test Location 2")

        self._go_to_devices_list()

    def _create_device(self, name, location=None):
        create_test_device(name=name, location_name=location, test_uuid=self.run_uuid)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def _go_to_devices_list(self):
        self.click_navbar_entry("Devices", "Devices")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_list"))

    def test_bulk_edit_require_selection(self):
        # Click "edit selected" without selecting anything
        self.click_bulk_edit()

        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_list"))
        self.assertTrue(self.browser.is_text_present("No devices were selected.", wait_time=5))

    def test_bulk_edit_all_devices(self):
        # Select all devices and edit them
        self.select_all_items()
        self.click_bulk_edit()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_bulk_edit"))

        # Edit serial number and submit form
        self.update_edit_form_value("serial", "Test Serial 2")
        self.submit_bulk_edit_operation()

        # Verify job output
        self.assertIsBulkEditJob()
        self.assertJobStatusIsCompleted()

        # Assert that data was changed
        found_devices = Device.objects.filter(serial="Test Serial 2").count()
        self.assertEqual(found_devices, 4)

    def test_bulk_edit_one_device(self):
        # Select one device and edit it
        self.select_one_item()
        self.click_bulk_edit()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_bulk_edit"))

        # Edit serial number and submit form
        self.update_edit_form_value("serial", "Test Serial 2")
        self.submit_bulk_edit_operation()

        # Verify job output
        self.assertIsBulkEditJob()
        self.assertJobStatusIsCompleted()

        # Assert that data was changed
        found_devices = Device.objects.filter(serial="Test Serial 2").count()
        self.assertEqual(found_devices, 1)

    def test_bulk_edit_all_filtered_devices(self):
        # Filter devices
        self.apply_filter("location", "Test Location 2")

        # Select all devices and edit them
        self.select_all_items()
        self.click_bulk_edit()
        self.assertIn(self.live_server_url + reverse("dcim:device_bulk_edit"), self.browser.url)

        # Edit serial number and submit form
        self.update_edit_form_value("serial", "Test Serial 2")
        self.submit_bulk_edit_operation()

        # Verify job output
        self.assertIsBulkEditJob()
        self.assertJobStatusIsCompleted()

        # Assert that data was changed
        found_devices = Device.objects.filter(serial="Test Serial 2").count()
        self.assertEqual(found_devices, 2)

    def test_bulk_edit_one_filtered_devices(self):
        # Filter devices
        self.apply_filter("location", "Test Location 2")

        # Select one device and edit it
        self.select_one_item()
        self.click_bulk_edit()
        self.assertIn(self.live_server_url + reverse("dcim:device_bulk_edit"), self.browser.url)

        # Edit serial number and submit form
        self.update_edit_form_value("serial", "Test Serial 2")
        self.submit_bulk_edit_operation()

        # Verify job output
        self.assertIsBulkEditJob()
        self.assertJobStatusIsCompleted()

        # Assert that data was changed
        found_devices = Device.objects.filter(serial="Test Serial 2").count()
        self.assertEqual(found_devices, 1)
