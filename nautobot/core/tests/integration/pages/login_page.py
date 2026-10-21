"""Page object for the login page (/login/)."""

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


class LoginPage(BasePage):
    """The login page. Use it with a page whose context has no saved login (`storage_state=None`)."""

    PATH = "/login/"

    _USERNAME_FIELD = "input[name='username']"

    def navigate(self):
        """Go to the login page."""
        self._goto(self.PATH)

    def expect_loaded(self):
        """Assert (auto-retrying) that the login form's username field is present."""
        expect(self.page.locator(self._USERNAME_FIELD)).to_be_attached()
