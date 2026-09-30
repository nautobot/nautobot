"""Computed fields on the Device detail and list views."""

import pytest

from nautobot.dcim.tests.integration.pages.device_detail_page import DeviceDetailPage
from nautobot.dcim.tests.integration.pages.devices_page import DevicesPage


class ComputedFieldsTestCase:
    """Computed-field placement on the Device detail view and the Device list column.

    Each `advanced_ui` setting has its own test, starting from a computed field created
    with that setting.
    """

    @pytest.mark.behavioral
    def test_computed_field_advanced_ui_false_renders_on_main_tab(
        self, auth_page, base_url, created_device, created_computed_field
    ):
        """A computed field with `advanced_ui` off renders on the main tab and not on the Advanced tab.

        Both the field's label and its rendered value are checked.
        """
        device = DeviceDetailPage(auth_page, base_url)
        device.navigate(created_device["id"])

        for text in (created_computed_field["label"], created_computed_field["expected_value"]):
            device.expect_tab_to_show("main", text)
            device.expect_tab_not_to_contain("advanced", text)

    @pytest.mark.behavioral
    def test_computed_field_advanced_ui_true_renders_on_advanced_tab(
        self, auth_page, base_url, created_device, created_advanced_ui_computed_field
    ):
        """A computed field with `advanced_ui` on renders only on the Advanced tab, not on the main tab.

        Both the field's label and its rendered value are checked.
        """
        device = DeviceDetailPage(auth_page, base_url)
        device.navigate(created_device["id"])
        device.open_tab("advanced")

        for text in (created_advanced_ui_computed_field["label"], created_advanced_ui_computed_field["expected_value"]):
            device.expect_tab_to_show("advanced", text)
            device.expect_tab_not_to_contain("main", text)

    @pytest.mark.behavioral
    def test_computed_field_appears_in_object_list(
        self, auth_page, base_url, api_computed_field_value, created_device, created_computed_field
    ):
        """A computed field can be shown as a Device list column, where it renders the API's value.

        The column is off by default. Turning it on in the table configuration shows the
        device's rendered value, and resetting the configuration removes the column again,
        which also leaves the shared user's Device table at its defaults.
        """
        label = created_computed_field["label"]
        api_value = api_computed_field_value("dcim/devices", created_device["id"], created_computed_field["key"])
        assert api_value == created_computed_field["expected_value"]

        devices = DevicesPage(auth_page, base_url)
        devices.navigate(name=created_device["name"])
        devices.expect_row_count(1)
        devices.expect_column_shown(label, shown=False)

        devices.toggle_table_column(label)
        devices.expect_column_shown(label)
        assert devices.get_column_values_by_header(label) == [api_value]

        devices.reset_table_columns()
        devices.expect_column_shown(label, shown=False)
