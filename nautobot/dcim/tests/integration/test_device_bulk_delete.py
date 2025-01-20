import uuid

from django.urls import reverse

from nautobot.core.testing.integration import BulkOperationsMixin, ObjectsListMixin, SeleniumTestCase
from nautobot.extras.tests.integration import create_test_device


class BulkDeleteDeviceTestCase(SeleniumTestCase, ObjectsListMixin, BulkOperationsMixin):
    """
    Test devices bulk delete.
    """

    def setUp(self):
        super().setUp()

        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        self.run_uuid = str(uuid.uuid4())

        # Create device for test
        self._create_device("Test Device Integration Test 1")
        self._create_device("Test Device Integration Test 2")
        self._create_device("Test Device Integration Test 3", location="Test Location 2")
        self._create_device("Test Device Integration Test 4", location="Test Location 2")

        self._go_to_devices_list()

    def tearDown(self):
        self.logout()
        super().tearDown()

    def _create_device(self, name, location=None):
        create_test_device(name=name, location_name=location, test_uuid=self.run_uuid)

    def _go_to_devices_list(self):
        self.click_navbar_entry("Devices", "Devices")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_list"))

    def test_bulk_delete_require_selection(self):
        # Click "delete selected" without selecting anything
        self.click_bulk_delete()

        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:device_list"))
        self.assertTrue(self.browser.is_text_present("No devices were selected for deletion.", wait_time=5))

    def test_bulk_delete_all_devices(self):
        # Select all devices and delete them
        self.select_all_items()
        self.click_bulk_delete()

        self.assertBulkDeleteConfirmMessageIsValid(4)
        self.confirm_bulk_delete_operation()

        # Verify job output
        self.assertIsBulkDeleteJob()
        self.assertJobStatusIsCompleted()

        self._go_to_devices_list()
        self.assertEqual(self.objects_list_visible_items, 0)

    def test_bulk_delete_one_device(self):
        # Select one device and delete it
        self.select_one_item()
        self.click_bulk_delete()

        self.assertBulkDeleteConfirmMessageIsValid(1)
        self.confirm_bulk_delete_operation()

        # Verify job output
        self.assertIsBulkDeleteJob()
        self.assertJobStatusIsCompleted()

        self._go_to_devices_list()
        self.assertEqual(self.objects_list_visible_items, 3)

    def test_bulk_delete_all_from_all_pages_devices(self):
        # Select all from all pages
        self.set_per_page()
        self.select_all_items_from_all_pages()
        self.click_bulk_delete_all()

        self.assertBulkDeleteConfirmMessageIsValid(4)
        self.confirm_bulk_delete_operation()

        # Verify job output
        self.assertIsBulkDeleteJob()
        self.assertJobStatusIsCompleted()

        self._go_to_devices_list()
        self.assertEqual(self.objects_list_visible_items, 0)

    def test_bulk_delete_all_filtered_devices(self):
        # Filter devices
        self.apply_filter("location", "Test Location 2")

        # Select all devices and delete them
        self.select_all_items()
        self.click_bulk_delete()
        self.confirm_bulk_delete_operation()

        # Verify job output
        self.assertIsBulkDeleteJob()
        self.assertJobStatusIsCompleted()

        self._go_to_devices_list()
        self.assertEqual(self.objects_list_visible_items, 2)

    def test_bulk_delete_one_filtered_devices(self):
        # Filter devices
        self.apply_filter("location", "Test Location 2")

        # Select one device and delete it
        self.select_one_item()
        self.click_bulk_delete()
        self.confirm_bulk_delete_operation()

        # Verify job output
        self.assertIsBulkDeleteJob()
        self.assertJobStatusIsCompleted()

        self._go_to_devices_list()
        self.assertEqual(self.objects_list_visible_items, 3)

    def test_bulk_delete_all_from_all_pages_filtered_devices(self):
        # Filter devices
        self.set_per_page()
        self.apply_filter("location", "Test Location 2")

        # Select all devices and delete them
        self.select_all_items_from_all_pages()
        self.click_bulk_delete_all()

        self.assertBulkDeleteConfirmMessageIsValid(2)
        self.confirm_bulk_delete_operation()

        # Verify job output
        self.assertIsBulkDeleteJob()
        self.assertJobStatusIsCompleted()

        self._go_to_devices_list()
        self.assertEqual(self.objects_list_visible_items, 2)


