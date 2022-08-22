from django.urls import reverse

from nautobot.utilities.testing.integration import SeleniumTestCase


class SwaggerUITestCase(SeleniumTestCase):
    """Integration tests for the Swagger UI."""

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_endpoint_render(self):
        """Check that the dcim.site API endpoints are rendered correctly."""
        self.browser.visit(self.live_server_url + reverse("api_docs"))
        # Wait for Swagger UI to load, look for the site-list endpoint in the UI and click on it to expand it.
        dcim_sites_list = self.browser.find_by_id("operations-dcim-dcim_sites_list", wait_time=20).first
        dcim_sites_list.find_by_tag("button").first.click()

        # Look for the "Try it out" button and click it
        dcim_sites_list.find_by_xpath("//button[contains(text(), 'Try it out')]").first.click()

        # Look for the "Execute" button and click it
        dcim_sites_list.find_by_xpath("//button[contains(text(), 'Execute')]").first.click()

        # Look at the response status code
        response_code = dcim_sites_list.find_by_xpath(
            "//table[@class[contains(.,'live-responses-table')]]/tbody//td[@class[contains(.,'response-col_status')]]",
            wait_time=20,
        ).first.text
        self.assertEqual(response_code, "200")
        # The response body is wrapped in a bunch of <span>s to apply syntax-highlighting, so it's not worth inspecting.
