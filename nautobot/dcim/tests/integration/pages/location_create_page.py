"""Page object for the Location add form (/dcim/locations/add/)."""

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


class LocationCreatePage(BasePage):
    """The Location add form."""

    ADD_PATH = "/dcim/locations/add/"

    _CREATE_BUTTON = "button[name='_create']"
    _INVALID_FIELD = "[aria-invalid='true']"

    def navigate(self):
        """Go to the add form and wait for its Create button."""
        self._goto(self.ADD_PATH)
        expect(self.page.locator(self._CREATE_BUTTON)).to_be_attached()

    def remove_required_attributes(self):
        """Remove every `required` attribute so the browser submits the form and the server can reject it."""
        self.page.evaluate(
            "document.querySelectorAll('[required]').forEach((element) => element.removeAttribute('required'))"
        )

    def submit(self):
        """Click Create."""
        self.page.click(self._CREATE_BUTTON)

    def expect_validation_errors(self):
        """Assert (auto-retrying) that the server rejected the form and marked at least one field invalid."""
        expect(self.page.locator(self._INVALID_FIELD).first).to_be_attached()
