from nautobot.utilities.testing.integration import SeleniumTestCase


class NavBarTestCase(SeleniumTestCase):
    """Integration test the naviagation menu."""

    def test_navbar_render(self):
        """
        Render navbar from home page.
        """
        self.login("bob", "bob")
        self.selenium.wait_for_html("body")
