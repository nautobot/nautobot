"""Device create form."""

import pytest

from nautobot.dcim.tests.integration.pages.device_create_page import DeviceCreatePage
from nautobot.dcim.tests.integration.pages.device_detail_page import DeviceDetailPage
from nautobot.playwright.helpers import unique_name


class CreateDeviceTestCase:
    """The Device create form."""

    @pytest.mark.behavioral
    def test_create_device(self, auth_page, base_url, api, create_object, created_device_prerequisites):
        """Saving the form creates the device with the picked values and opens its detail view."""
        name = unique_name()
        create_object.track("dcim/devices/", name=name)
        form = DeviceCreatePage(auth_page, base_url)
        form.navigate()
        form.fill_required_fields(
            name=name,
            location=created_device_prerequisites["location"],
            device_type=created_device_prerequisites["device_type"],
            role=created_device_prerequisites["role"],
            status=created_device_prerequisites["status"],
        )
        form.submit()
        detail = DeviceDetailPage(auth_page, base_url)
        detail.expect_flash_message(f"Created device {name}")

        response = api.get("/api/dcim/devices/", params={"name": name})
        assert response.ok, f"GET /api/dcim/devices/ returned {response.status}: {response.text()[:200]}"
        saved = response.json()["results"]
        assert len(saved) == 1, f"Expected one device named {name}, found {len(saved)}"
        device = saved[0]
        assert device["location"]["id"] == created_device_prerequisites["location"]["id"]
        assert device["device_type"]["id"] == created_device_prerequisites["device_type"]["id"]
        assert device["role"]["id"] == created_device_prerequisites["role"]["id"]
        assert device["status"]["id"] == created_device_prerequisites["status"]["id"]

        detail.expect_url_contains(DeviceDetailPage.DETAIL_PATH.format(pk=device["id"]))
        detail.expect_heading(name)
        detail.expect_panel_field("Device", "Location", created_device_prerequisites["location"]["name"])
        detail.expect_panel_field("Device", "Device Type", created_device_prerequisites["device_type"]["model"])
        detail.expect_panel_field("Management", "Role", created_device_prerequisites["role"]["name"])
        detail.expect_panel_field("Management", "Status", created_device_prerequisites["status"]["name"])
