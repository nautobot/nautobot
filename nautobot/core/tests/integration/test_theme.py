from nautobot.utilities.testing.integration import SeleniumTestCase


class ThemeTestCase(SeleniumTestCase):
    """Integration test to check theme selection modal functionality."""

    def test_modal_not_rendered(self):
        """As implemented, modal dialog box does not render until activated."""

        self.browser.visit(self.live_server_url)
        # Modal dialog box should not load on page load
        self.assertEqual(len(self.browser.find_by_xpath("//div[@class[contains(., 'modal-backdrop')]]")), 0)

        # Validate only one instance of modal present
        theme_modal = self.browser.find_by_xpath("//div[@id[contains(., 'theme_modal')]]")
        self.assertEqual(len(theme_modal), 1)

        # Validate modal is not visible
        self.assertFalse(theme_modal[0].visible)

    def test_modal_rendered(self):
        """Modal should render when selecting the 'theme' button in the footer."""

        self.browser.visit(self.live_server_url)

        # Validate only one instance of modal present
        self.browser.find_by_xpath(".//a[@id='btn-theme-modal']").click()
        self.assertEqual(len(self.browser.find_by_xpath("//div[@class[contains(., 'modal-backdrop')]]")), 1)

        # Validate modal is visible
        theme_modal = self.browser.find_by_xpath("//div[@id[contains(., 'theme_modal')]]")
        self.assertTrue(theme_modal[0].visible)

        # Validate 3 themes available to select
        self.assertEqual(
            len(self.browser.find_by_xpath("//div[@class[contains(., 'modal-body')]]//tbody/tr")), 1
        )  # 1 row

        columns = self.browser.find_by_xpath("//div[@class[contains(., 'modal-body')]]//tbody/tr/td")
        self.assertEqual(len(columns), 3)  # 3 columns (light, dark, system)

        # Validate 3 modes in order are light, dark, and system
        self.assertIn("light", columns[0].html)
        self.assertIn("dark", columns[1].html)
        self.assertIn("system", columns[2].html)

        # Validate only System theme is selected by default
        system_theme = self.browser.find_by_xpath(".//td[@id='td-light-theme']")
        self.assertFalse(system_theme[0].has_class("active-theme"))
        system_theme = self.browser.find_by_xpath(".//td[@id='td-dark-theme']")
        self.assertFalse(system_theme[0].has_class("active-theme"))
        system_theme = self.browser.find_by_xpath(".//td[@id='td-system-theme']")
        self.assertTrue(system_theme[0].has_class("active-theme"))

        # Validate Modal closes when cancel button clicked
        self.browser.find_by_xpath(".//button[@id='dismiss-modal-theme']").click()
        self.assertFalse(theme_modal[0].visible)
