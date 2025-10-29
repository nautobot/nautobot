from nautobot.core.testing.integration import SeleniumTestCase


class ThemeTestCase(SeleniumTestCase):
    """Integration test to check theme selection modal functionality."""

    def setUp(self):
        super().setUp()
        self.login(self.user.username, self.password)

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
        theme_modal = self.browser.find_by_xpath("//div[@id='theme_modal']")
        self.assertTrue(theme_modal[0].is_visible(wait_time=5))

        # Validate 3 themes available to select
        columns = self.browser.find_by_xpath("//div[@class[contains(., 'modal-body')]]//dl/dt")
        self.assertEqual(len(columns), 3)  # 3 columns (light, dark, system)

        # Validate 3 modes in order are light, dark, and system
        self.assertIn("Light", columns[0].html)
        self.assertIn("Dark", columns[1].html)
        self.assertIn("System", columns[2].html)

        # Validate only System theme is selected by default
        light_theme = self.browser.find_by_xpath(".//dd/button[@data-nb-theme='light']")
        self.assertFalse(light_theme[0].has_class("border"))
        self.assertFalse(light_theme[0].has_class("border-primary"))
        dark_theme = self.browser.find_by_xpath(".//dd/button[@data-nb-theme='dark']")
        self.assertFalse(dark_theme[0].has_class("border"))
        self.assertFalse(dark_theme[0].has_class("border-primary"))
        system_theme = self.browser.find_by_xpath(".//dd/button[@data-nb-theme='system']")
        self.assertTrue(system_theme[0].has_class("border"))
        self.assertTrue(system_theme[0].has_class("border-primary"))

        # Why is it required to click the cancel button twice? I honestly don't know, but for some reason Selenium seems
        # to have troubles here. The first press only focuses the cancel button, and only after clicking it for the
        # second time, the modal closes successfully.
        self.browser.find_by_xpath(".//button[@id='dismiss-modal-theme']").click()
        self.browser.find_by_xpath(".//button[@id='dismiss-modal-theme']").click()

        # Validate Modal closes when cancel button clicked
        self.assertTrue(theme_modal[0].is_not_visible(wait_time=5))
