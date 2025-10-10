from django.test import tag

from nautobot.core.testing.integration import SeleniumTestCase


@tag("example_app")
class AppNavBarTestCase(SeleniumTestCase):
    """Integration test the navigation menu."""

    navbar = {
        "Circuits": {
            "Circuits": {
                "Circuits": {
                    "buttons": ["Add"],
                },
                "Circuit Types": {
                    "buttons": ["Add"],
                },
            },
            "Example Circuit Group": {
                "Example Models": {
                    "buttons": ["Add"],
                },
            },
            "Providers": {
                "Providers": {
                    "buttons": ["Add"],
                },
            },
        },
        "Apps": {
            "Example Nautobot App": {
                "Example Models": {
                    "buttons": ["Add"],
                },
                "Another Example Models": {
                    "buttons": ["Add"],
                },
            },
        },
    }

    def setUp(self):
        super().setUp()
        self.login_as_superuser()
        self.browser.visit(self.live_server_url)

    def test_app_navbar_new_tab(self):
        """
        Verify that a new menu tab defined and populated by the example app is rendered properly.
        """
        sidenav_section = self.find_sidenav_section("Example Menu")
        sidenav_section.toggle()
        self.assertTrue(sidenav_section.is_expanded)

        group = sidenav_section.flyout.find_by_xpath(
            "//li[@class='nb-sidenav-link-group' and normalize-space()='Example Group 1']"
        )
        self.assertEqual(len(group), 1)

        link = sidenav_section.find_link("Example Models")
        self.assertEqual(len(link), 1)

    def test_app_navbar_modify_circuits(self):
        """
        Verify that the example app is able to add a new group and items to an existing menu tab.
        """
        sidenav_section = self.find_sidenav_section("Circuits")
        sidenav_section.toggle()
        self.assertTrue(sidenav_section.is_expanded)

        for group_name, items in self.navbar["Circuits"].items():
            group = sidenav_section.flyout.find_by_xpath(
                f"//li[@class='nb-sidenav-link-group' and normalize-space()='{group_name}']"
            )
            self.assertEqual(len(group), 1)

            for item_name, _ in items.items():
                link = sidenav_section.find_link(item_name)
                self.assertEqual(len(link), 1)

        sidenav_section.toggle()

    def test_app_navbar_apps_tab(self):
        """
        Test that old-style app menu definitions are correctly rendered to the Apps menu tab.
        """
        sidenav_section = self.find_sidenav_section("Apps")
        sidenav_section.toggle()
        self.assertTrue(sidenav_section.is_expanded)

        for group_name, items in self.navbar["Apps"].items():
            group = sidenav_section.flyout.find_by_xpath(
                f"//li[@class='nb-sidenav-link-group' and normalize-space()='{group_name}']"
            )
            self.assertEqual(len(group), 1)

            for item_name, _ in items.items():
                link = sidenav_section.find_link(item_name)
                self.assertEqual(len(link), 1)

        sidenav_section.toggle()

    def test_app_navbar_state_persistence(self):
        """
        Verify that menu expanded/collapse state is persistent and does not reset after page refresh.
        """

        def get_toggler(aria_expanded):
            return self.browser.find_by_xpath(
                f"//*[@id='sidenav']//button[contains(@class, 'nb-sidenav-toggler') and @aria-expanded='{aria_expanded}']"
            )

        toggler = get_toggler("true")  # Get toggler, expect sidenav to be expanded by default.
        self.assertTrue(toggler)

        toggler.click()  # Collapse sidenav.
        self.browser.reload()
        toggler = get_toggler("false")  # Get toggler, expect sidenav to stay collapsed after full document reload.
        self.assertTrue(toggler)

        toggler.click()  # Expand sidenav.
        self.browser.reload()
        toggler = get_toggler("true")  # Get toggler, expect sidenav to be expanded again.
        self.assertTrue(toggler)
