from django.urls import reverse

from nautobot.core.testing.integration import BulkOperationsMixin, ObjectsListMixin, SeleniumTestCase


class BulkDeleteDeviceTestCase(SeleniumTestCase, ObjectsListMixin, BulkOperationsMixin):
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

        # Create device for test
        self._create_device("Test Device Integration Test 1")
        self._create_device("Test Device Integration Test 2")
        self._create_device("Test Device Integration Test 3", location="Test Location 2")
        self._create_device("Test Device Integration Test 4", location="Test Location 2")

        self._go_to_devices_list()

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
        self.logout()
        super().tearDown()

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
        self.set_per_page(25)  # Set page size back to default
        self.assertEqual(self.objects_list_visible_items, 2)

        self.apply_filter("location", "Test Location 2")
        self.assertEqual(self.objects_list_visible_items, 0)
