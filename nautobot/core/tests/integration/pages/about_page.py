"""Page object for the About page (/about/)."""

from nautobot.playwright.base_page import BasePage


class AboutPage(BasePage):
    """The About page, a static core page every installation has."""

    PATH = "/about/"

    def navigate(self):
        """Go to the About page."""
        self._goto(self.PATH)
