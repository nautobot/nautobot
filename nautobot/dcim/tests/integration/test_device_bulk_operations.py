"""Device bulk edit and bulk delete."""

import pytest

from nautobot.dcim.tests.integration.pages.devices_page import DevicesPage
from nautobot.playwright import bulk_operations


class DeviceBulkOperationsTestCase(bulk_operations.BulkOperationsTestCase):
    """Device bulk edit and bulk delete, through the shared bulk operations tests."""

    page_class = DevicesPage
    model_base_viewname = "dcim:device"
    model_edit_data = {"serial": "Test serial"}
    model_filter_by = {"location": "{prefix}-location-2"}

    def setup_items(self, create_object, status_for, prefix):
        """Create five devices: three in one location, and two in the location that model_filter_by selects."""
        location_type = create_object(
            "dcim/location-types/", name=f"{prefix}-location-type", content_types=["dcim.device"]
        )
        location_status = status_for("dcim.location")["id"]
        locations = [
            create_object(
                "dcim/locations/",
                name=f"{prefix}-location-{index}",
                location_type=location_type["id"],
                status=location_status,
            )
            for index in (1, 2)
        ]
        manufacturer = create_object("dcim/manufacturers/", name=f"{prefix}-manufacturer")
        device_type = create_object("dcim/device-types/", model=f"{prefix}-model", manufacturer=manufacturer["id"])
        role = create_object("extras/roles/", name=f"{prefix}-role", content_types=["dcim.device"])
        device_status = status_for("dcim.device")["id"]
        for index, location in enumerate([locations[0]] * 3 + [locations[1]] * 2, start=1):
            create_object(
                "dcim/devices/",
                name=f"{prefix}-device-{index}",
                location=location["id"],
                device_type=device_type["id"],
                role=role["id"],
                status=device_status,
            )


class DeviceBulkUrlParamTestCase:
    """The bulk edit form, opened from a device list filtered by device type."""

    @pytest.mark.behavioral
    def test_param_fills_device_type(self, device_bulk_edit_form, created_device):
        """The bulk edit form leaves Device Type unset, even though the list it came from is filtered by device type.

        The device_type parameter is in the form's URL. If the form filled the field from
        it, applying the form would set every selected device to that type.
        """
        device_bulk_edit_form.expect_url_contains(f"device_type={created_device['device_type']['id']}")
        device_bulk_edit_form.expect_bulk_edit_dropdown_unset("device_type")


class DeviceBulkEditNullifyTestCase:
    """Set null on the device bulk edit form.

    Regression test for https://github.com/nautobot/nautobot/issues/8981.
    """

    def test_set_null_hides_dropdown_field(self, device_bulk_edit_form):
        """Checking a dropdown field's Set null box hides its Select2 widget."""
        # Platform is a nullable dropdown, shown as a Select2 widget.
        device_bulk_edit_form.expect_bulk_edit_dropdown("platform")

        device_bulk_edit_form.set_null("platform")

        device_bulk_edit_form.expect_no_bulk_edit_dropdown("platform")
