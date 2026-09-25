"""Page object for the Device detail view (/dcim/devices/<pk>/)."""

from playwright.sync_api import expect

from nautobot.playwright.detail_page import DetailPage


class DeviceDetailPage(DetailPage):
    """The Device detail view. Heading, panels and deferred components come from DetailPage."""

    DETAIL_PATH = "/dcim/devices/{pk}/"
    VERBOSE_NAME = "Device"

    # Devices add one button of their own beside the standard detail-view actions.
    _ADD_COMPONENTS_BUTTON = "#device-add-components-button"

    def expect_add_components_button(self):
        """Assert (auto-retrying) that the Add Components dropdown button is rendered."""
        expect(self.page.locator(self._ADD_COMPONENTS_BUTTON)).to_contain_text("Add Components")
