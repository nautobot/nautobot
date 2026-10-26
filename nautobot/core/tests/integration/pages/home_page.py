"""Page object for the home page (/)."""

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


class HomePage(BasePage):
    """The home page, a grid of panels the user can drag into their own order."""

    PATH = "/"

    _PANELS = "#draggable-homepage-panels"

    def navigate(self):
        """Go to the home page."""
        self._goto(self.PATH)

    def expect_loaded(self):
        """Assert (auto-retrying) that the panel grid, which only the home page renders, is present."""
        expect(self.page.locator(self._PANELS)).to_be_attached()
