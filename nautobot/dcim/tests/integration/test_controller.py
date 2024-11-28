from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.extras.models import JobResult


class ControllerTestCase(SeleniumTestCase):
    """
    Perform set of Controller tests using Selenium.
    """

    def test_controller_bulk_edit(self):
        """
        This test goes through the process of creating a Controller and performing bulk edit.
        """
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        # Create LocationType
        self.click_navbar_entry("Organization", "Location Types")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:locationtype_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:locationtype_add"))
        self.fill_select2_multiselect_field("content_types", "dcim | controller")
        self.browser.fill("name", "Test Location Type 1")
        self.click_edit_form_create_button()

        # Create Location
        self.click_navbar_entry("Organization", "Locations")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:location_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:location_add"))
        self.fill_select2_field("location_type", "Test Location Type 1")
        self.fill_select2_field("status", "")  # pick first status
        self.browser.fill("name", "Test Location 1")
        self.click_edit_form_create_button()

        # Create Controller
        self.click_navbar_entry("Devices", "Controllers")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:controller_list"))
        self.click_list_view_add_button()
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:controller_add"))
        self.browser.fill("name", "Test Controller Integration Test 1")
        self.fill_select2_field("location", "Test Location 1")
        self.fill_select2_field("status", "")  # pick first status
        self.click_edit_form_create_button()

        # Test bulk edit
        self.click_navbar_entry("Devices", "Controllers")
        self.assertEqual(self.browser.url, self.live_server_url + reverse("dcim:controller_list"))
        self.browser.find_by_xpath("//input[@name='pk']").click()
        bulk_edit_url = reverse("dcim:controller_bulk_edit")
        self.browser.find_by_xpath(f"//button[@formaction='{bulk_edit_url}']").click()

        # Submit bulk edit form without any changes
        self.browser.find_by_xpath("//button[@name='_apply']", wait_time=5).click()

        job_result = JobResult.objects.filter(name="Bulk Edit Objects").first()
        self.assertEqual(
            self.browser.url, self.live_server_url + reverse("extras:jobresult", args=[job_result.pk]) + "?tab=main"
        )
