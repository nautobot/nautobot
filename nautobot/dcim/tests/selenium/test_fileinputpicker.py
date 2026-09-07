from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Job, Status


class ClearableFileInputTestCase(SeleniumTestCase):
    def setUp(self):
        super().setUp()
        self.login_as_superuser()

    def _assert_file_picker(self, uri_to_visit: str, page_loaded_confirmation: str, file_input_selector_id: str):
        """
        Ensure clearable input file type has working clear and info display.
        """
        self.browser.visit(f"{self.live_server_url}{uri_to_visit}")
        self.assertTrue(self.browser.is_text_present(page_loaded_confirmation, wait_time=10))

        # Find the first file input button and scroll to it
        front_image_file_input = self.browser.find_by_id(file_input_selector_id).first
        self.scroll_element_into_view(element=front_image_file_input)

        # Test file text changes after selecting a file
        self.assertEqual(front_image_file_input.value, "")
        front_image_file_input.fill("/dev/null")
        self.assertEqual(front_image_file_input.value, "C:\\fakepath\\null")

        # clicking clearbutton should wipe the file input value
        clear_button = self.browser.find_by_css(f"#{file_input_selector_id} + button").first
        clear_button.click()
        self.assertEqual(front_image_file_input.value, "")

    def test_add_device_page(self):
        """
        Confirm device type add page input is working correctly.
        """
        self._assert_file_picker(
            uri_to_visit=reverse("dcim:devicetype_add"),
            page_loaded_confirmation="Add a new device type",
            file_input_selector_id="id_front_image",
        )

    def test_job_runner_page(self):
        """
        Confirm job run page file input is working correctly.
        """
        example_job = Job.objects.get(name="Example File Input/Output job").pk
        job_example_file_uri = reverse("extras:job_run", kwargs={"pk": example_job})
        self._assert_file_picker(
            uri_to_visit=job_example_file_uri,
            page_loaded_confirmation="Example File",
            file_input_selector_id="id_input_file",
        )

    def test_location_image_attachment_view(self):
        """
        Confirm location image attachment page is working correctly.
        """
        location_type, _ = LocationType.objects.get_or_create(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        location, _ = Location.objects.get_or_create(
            name="Test Location 1", location_type=location_type, status=location_status
        )
        location_image_attach_uri = reverse(
            "dcim:location_add_image", kwargs={"object_id": location.id, "model": Location}
        )
        self._assert_file_picker(
            uri_to_visit=location_image_attach_uri,
            page_loaded_confirmation="IMAGE ATTACHMENT",
            file_input_selector_id="id_image",
        )
