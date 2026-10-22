"""Page object for the Location add form (/dcim/locations/add/)."""

from playwright.sync_api import expect

from nautobot.playwright.form_page import FormPage


class LocationCreatePage(FormPage):
    """The Location add form."""

    ADD_PATH = "/dcim/locations/add/"

    _INVALID_FIELD = "[aria-invalid='true']"

    def remove_required_attributes(self):
        """Remove every `required` attribute so the browser submits the form and the server can reject it."""
        self.page.evaluate(
            "document.querySelectorAll('[required]').forEach((element) => element.removeAttribute('required'))"
        )

    def expect_validation_errors(self):
        """Assert (auto-retrying) that the server rejected the form and marked at least one field invalid."""
        expect(self.page.locator(self._INVALID_FIELD).first).to_be_attached()
