from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase, WebDriverWait
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Job, Status


class ClearableFileInputTestCase(SeleniumTestCase):
    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def _assert_file_picker(self, uri_to_visit: str, page_loaded_confirmation: str, file_input_selector_id: str):
        """
        Ensure clearable input file type has working clear and info display.
        """
        self.browser.visit(f"{self.live_server_url}{uri_to_visit}")
        WebDriverWait(self.browser, 10).until(lambda driver: driver.is_text_present(page_loaded_confirmation))

        # Find the first file input button and scroll to it
        front_image_button = self.browser.find_by_css("span.group-span-filestyle.input-group-btn").first
        front_image_button.scroll_to()

        # cancel button is NOT visible initially
        self.assertFalse(self.browser.find_by_css("button.clear-button").first.visible)

        # Test file text changes after selecting a file
        file_selection_indicator_css = "div.bootstrap-filestyle input[type='text'].form-control"
        self.assertEqual(self.browser.find_by_css(file_selection_indicator_css).first.value, "")
        front_image_file_input = self.browser.find_by_id(file_input_selector_id).first
        front_image_file_input.value = "/dev/null"
        self.assertEqual(self.browser.find_by_css(file_selection_indicator_css).first.value, "null")

        # clear button is now visible
        clear_button = self.browser.find_by_css("button.clear-button").first
        self.assertTrue(clear_button.visible)

        # clicking clearbutton should hide the button, and wipe the file input value
        clear_button.click()
        self.assertFalse(clear_button.visible)
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
            page_loaded_confirmation="Image attachment",
            file_input_selector_id="id_image",
        )
