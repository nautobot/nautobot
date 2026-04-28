from unittest import mock

from django.urls import reverse

from nautobot.core.testing.integration import SeleniumTestCase
from nautobot.core.ui.object_detail import Button, Panel
from nautobot.extras.tests.integration import create_test_device


class DeviceDetailTestCase(SeleniumTestCase):
    """Integration tests for Device detail view rendering."""

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

        self.device = create_test_device("Device 1")

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_device_detail_renders_fully(self):
        """Test that the Device detail page contains all expected panels and other content."""
        self.browser.visit(self.live_server_url + reverse("dcim:device", kwargs={"pk": self.device.pk}))

        # Page title
        self.assertTrue(self.browser.is_text_present(self.device.name))
        # Tab titles? TODO
        # Created date? TODO
        # Last updated date - as this is relative time, skip it
        # Buttons
        self.assertTrue(self.browser.is_text_present("Add Components", wait_time=5))
        self.assertTrue(self.browser.is_text_present("Edit Device", wait_time=5))
        # Device panel contents
        self.assertTrue(self.browser.is_text_present(self.device.location.name, wait_time=5))
        self.assertTrue(self.browser.is_text_present(self.device.device_type.model, wait_time=5))
        # Management panel contents
        self.assertTrue(self.browser.is_text_present(self.device.role.name, wait_time=5))
        self.assertTrue(self.browser.is_text_present(self.device.status.name, wait_time=5))
        # Comments panel contents
        # Tags panel contents
        self.assertTrue(self.browser.is_text_present("No tags assigned", wait_time=5))
        # Assigned VRFs panel contents
        self.assertTrue(self.browser.is_text_present("No VRF-device assignments found", wait_time=5))
        # Clusters panel contents
        self.assertTrue(self.browser.is_text_present("No clusters found", wait_time=5))
        # Services panel contents
        self.assertTrue(self.browser.is_text_present("No services found", wait_time=5))
        # Images panel contents
        self.assertTrue(self.browser.is_text_present("No image attachments found", wait_time=5))
        # Virtual Device Contexts panel contents
        self.assertTrue(self.browser.is_text_present("No virtual device contexts found", wait_time=5))
        # Panel titles
        panel_titles = [elem.text.lower() for elem in self.browser.find_by_css(".card-header strong")]
        self.assertIn("device", panel_titles)
        # self.assertIn("virtual chassis", panel_titles)  # not applicable to self.device
        self.assertIn("management", panel_titles)
        self.assertIn("comments", panel_titles)
        self.assertIn("tags", panel_titles)
        # self.assertIn("power utilization", panel_titles)  # not applicable to self.device
        self.assertIn("assigned vrfs", panel_titles)
        self.assertIn("clusters", panel_titles)
        self.assertIn("services", panel_titles)
        self.assertIn("images", panel_titles)
        self.assertIn("virtual device contexts", panel_titles)

    def test_device_detail_renders_fully_with_deferred_rendering(self):
        """Repeat test_device_detil_renders_fully() with deferred rendering of components enabled."""
        with mock.patch.object(Button, "deferred_render", True), mock.patch.object(Panel, "deferred_render", True):
            self.test_device_detail_renders_fully()
