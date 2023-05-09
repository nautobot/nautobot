from unittest import skipIf

from django.conf import settings

from nautobot.core.testing.integration import SeleniumTestCase


@skipIf(
    "example_plugin" not in settings.PLUGINS,
    "example_plugin not in settings.PLUGINS",
)
class PluginNavBarTestCase(SeleniumTestCase):
    """Integration test the navigation menu."""

    fixtures = ["user-data.json"]
    navbar = {
        "Inventory": {
            "Example App": {
                "Example Model": {
                    "permission": "example_plugin.view_examplemodel",
                },
            },
            "Circuits": {
                "Circuits": {
                    "permission": "circuits.view_circuit",
                },
                "Circuit Types": {
                    "permission": "circuits.view_circuittype",
                },
                "Providers": {
                    "permission": "circuits.view_provider",
                },
            },
        },
    }

    def setUp(self):
        super().setUp()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_plugin_navbar_modify_context(self):
        """
        Verify that the example plugin is able to add a new group and items to an existing menu tab/context.
        """
        # Set test user to admin
        self.user.is_superuser = True
        self.user.save()

        # Retrieve home page
        self.browser.visit(self.live_server_url)

        tab_xpath = "//*[@id='navbar']//*[contains(text(), 'Inventory')]"
        tab = self.browser.find_by_xpath(tab_xpath)
        tab.click()
        self.assertTrue(bool(tab["aria-expanded"]))

        for group_name, items in self.navbar["Inventory"].items():
            group = tab.find_by_xpath(f"{tab_xpath}/following-sibling::ul//li[contains(text(), '{group_name}')]")
            for item_name in items:
                item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[contains(text(), '{item_name}')]]"
                group.find_by_xpath(item_xpath)
