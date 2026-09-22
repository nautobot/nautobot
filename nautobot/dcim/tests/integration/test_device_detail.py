"""Device detail view rendering."""

import pytest

from nautobot.dcim.tests.integration.pages.device_detail_page import DeviceDetailPage

PANEL_TITLES = (
    "Device",
    "Management",
    "Comments",
    "Tags",
    "Assigned VRFs",
    "Clusters",
    "Services",
    "Images",
    "Virtual Device Contexts",
)

EMPTY_PANEL_TEXT = {
    "Tags": "No tags assigned",
    "Assigned VRFs": "No VRF-device assignments found",
    "Clusters": "No clusters found",
    "Services": "No services found",
    "Images": "No image attachments found",
    "Virtual Device Contexts": "No virtual device contexts found",
}


class DeviceDetailTestCase:
    """Tests that the Device detail page renders its expected panels and shows the device's data correctly."""

    def test_heading_and_action_buttons(self, auth_page, base_url, created_device):
        """The detail page is headed by the device's name and offers Add Components and Edit Device."""
        detail = DeviceDetailPage(auth_page, base_url)
        detail.navigate(created_device["device"]["id"])

        detail.expect_heading(created_device["device"]["name"])
        detail.expect_add_components_button()
        detail.expect_edit_button()

    def test_main_tab_panel_titles(self, auth_page, base_url, created_device):
        """Every panel a device with no related objects renders is present, exactly once."""
        detail = DeviceDetailPage(auth_page, base_url)
        detail.navigate(created_device["device"]["id"])

        for title in PANEL_TITLES:
            detail.expect_panel(title)

    def test_empty_panels_show_their_empty_state(self, auth_page, base_url, created_device):
        """Each panel with nothing to show says so, in its own body.

        A new device has no tags, VRF assignments, clusters, services, images or virtual
        device contexts, so all six panels render their empty state.
        """
        detail = DeviceDetailPage(auth_page, base_url)
        detail.navigate(created_device["device"]["id"])

        for title, empty_text in EMPTY_PANEL_TEXT.items():
            detail.expect_panel_to_contain(title, empty_text)

    @pytest.mark.behavioral
    def test_device_and_management_panel_values(self, auth_page, base_url, created_device):
        """The Device and Management panels show the values the device was created with."""
        detail = DeviceDetailPage(auth_page, base_url)
        detail.navigate(created_device["device"]["id"])

        detail.expect_panel_field("Device", "Location", created_device["location"]["name"])
        detail.expect_panel_field("Device", "Device Type", created_device["device_type"]["model"])
        detail.expect_panel_field("Management", "Role", created_device["role"]["name"])
        detail.expect_panel_field("Management", "Status", created_device["status"]["name"])

    @pytest.mark.behavioral
    def test_deferred_power_utilization_panel(self, auth_page, base_url, created_pdu):
        """The Power Utilization panel arrives in its own request, after a placeholder.

        Failing that request first proves the body is not in the document the server
        sends: the placeholder stays and the panel never appears. Allowing it then shows
        the body arriving, listing the device's own power port.
        """
        detail = DeviceDetailPage(auth_page, base_url)
        device_id = created_pdu["device"]["id"]

        detail.fail_deferred_components()
        detail.navigate(device_id)
        detail.expect_deferred_placeholder_count(1)
        detail.expect_no_panel("Power Utilization")

        detail.allow_deferred_components()
        detail.navigate(device_id)
        detail.expect_deferred_placeholder_count(0)
        detail.expect_panel("Power Utilization")
        detail.expect_panel_to_contain("Power Utilization", created_pdu["power_port"]["name"])
