from nautobot.utilities.testing.integration import SeleniumTestCase


class PluginBannerTestCase(SeleniumTestCase):
    """Integration test for rendering of plugin-injected banner content."""

    fixtures = ("user-data",)

    def test_banner_not_rendered(self):
        """As implemented, plugin banner does not render if the user is not logged in.

        More generally this tests the case where the registered banner() function returns None is handled correctly.
        """
        self.browser.visit(self.live_server_url)

        banners_html = self.browser.find_by_css(".plugin-banner")
        self.assertEqual(0, len(banners_html))

    def test_banner_rendered(self):
        """Plugin banner renders correctly if the user is logged in."""
        self.login(self.user.username, self.password)

        self.browser.visit(self.live_server_url)

        try:
            banners_html = self.browser.find_by_css(".plugin-banner")
            self.assertEqual(1, len(banners_html))
            self.assertIn(f"Hello, <strong>{self.user.username}</strong>", banners_html.first["innerHTML"])
        finally:
            self.logout()
