"""Device bulk edit and bulk delete."""

from nautobot.dcim.tests.integration.pages.devices_page import DevicesPage

# Imported as a module: a BulkOperationsTestCase in this namespace would be collected and run on its own.
from nautobot.playwright import bulk_operations


class DeviceBulkOperationsTestCase(bulk_operations.BulkOperationsTestCase):
    """Device bulk edit and bulk delete, through the shared bulk operations tests."""

    model_base_viewname = "dcim:device"
    model_edit_data = {"serial": "Test serial"}
    model_filter_by = {"location": "{prefix}-location-2"}

    def setup_items(self, create_object, status_for, prefix):
        """Five devices: three in one location, and the two that model_filter_by selects in another."""
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


def open_bulk_edit_form(page, base_url, created_device):
    """Select *created_device* on the device list, filtered by its device type, and open the bulk edit form."""
    devices = DevicesPage(page, base_url)
    devices.navigate(device_type=created_device["device_type"]["id"])
    devices.select_row(created_device["device"]["name"])
    devices.click_edit_selected()
    return devices


class DeviceBulkUrlParamTestCase:
    """The bulk edit form, opened from a device list filtered by device type."""

    def test_param_fills_device_type(self, auth_page, base_url, created_device):
        """The bulk edit form leaves Device Type unset, even though the list it came from is filtered by device type.

        The method name is the Selenium test's, and says the opposite of what it asserts.
        The device_type parameter does reach the bulk edit form, which the URL check
        proves. The form must not fill it in, or applying the form would set every
        selected device to that type.
        """
        devices = open_bulk_edit_form(auth_page, base_url, created_device)

        devices.expect_url_contains(f"device_type={created_device['device_type']['id']}")
        devices.expect_bulk_edit_dropdown_unset("device_type")


class DeviceBulkEditNullifyTestCase:
    """Set null on the device bulk edit form.

    Regression test for https://github.com/nautobot/nautobot/issues/8981.
    """

    def test_set_null_hides_dropdown_field(self, auth_page, base_url, created_device):
        """Checking a dropdown field's Set null box hides its Select2 widget."""
        devices = open_bulk_edit_form(auth_page, base_url, created_device)
        # Platform is a nullable dropdown, shown as a Select2 widget.
        devices.expect_bulk_edit_dropdown_visible("platform")

        devices.set_null("platform")

        devices.expect_bulk_edit_dropdown_visible("platform", visible=False)
