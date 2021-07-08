from nautobot.utilities.testing.integration import SeleniumTestCase


class HomeTestCase(SeleniumTestCase):
    """Integration tests against the home page."""

    fixtures = ["user-data.json"]  # bob/bob

    def test_login(self):
        """
        Perform a UI login.
        """

        self.login("bob", "bob")

        # Wait for the page to render and make sure we got a body.
        self.selenium.wait_for_html("body")
