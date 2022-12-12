from unittest import skipIf

from django.conf import settings

from nautobot.utilities.choices import ButtonActionColorChoices, ButtonActionIconChoices
from nautobot.utilities.testing.integration import SeleniumTestCase


@skipIf(
    "example_plugin" not in settings.PLUGINS,
    "example_plugin not in settings.PLUGINS",
)
class PluginNavBarTestCase(SeleniumTestCase):
    """Integration test the navigation menu."""

    fixtures = ["user-data.json"]
    navbar = {
        "Example Menu": {
            "Example Group 1": {
                "Example Model": {
                    "permission": "example_plugin.view_examplemodel",
                    "buttons": ["Add", "Import"],
                },
            },
        },
        "Circuits": {
            "Circuits": {
                "Circuits": {
                    "permission": "circuits.view_circuit",
                    "buttons": ["Add", "Import"],
                },
                "Circuit Type": {
                    "permission": "circuits.view_circuittype",
                    "buttons": ["Add", "Import"],
                },
            },
            "Example Circuit Group": {
                "Example Model": {
                    "permission": "example_plugin.view_examplemodel",
                    "buttons": ["Add", "Import"],
                },
            },
            "Providers": {
                "Providers": {
                    "permission": "circuits.view_provider",
                    "buttons": ["Add", "Import"],
                },
            },
        },
        "Plugins": {
            "Example Nautobot App": {
                "Models": {
                    "permission": "example_plugin.view_examplemodel",
                    "buttons": ["Add a new example model", "Import example models"],
                },
                "Other Models": {
                    "permission": "example_plugin.view_examplemodel",
                    "buttons": [],
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

    def test_plugin_navbar_new_tab(self):
        """
        Verify that a new menu tab defined and populated by the example plugin is rendered properly.
        """
        # Set test user to admin
        self.user.is_superuser = True
        self.user.save()

        # Retrieve home page
        self.browser.visit(self.live_server_url)

        tab_xpath = "//*[@id='navbar']//*[contains(text(), 'Example Menu')]"
        tab = self.browser.find_by_xpath(tab_xpath)
        tab.click()
        self.assertTrue(bool(tab["aria-expanded"]))

        group = tab.find_by_xpath(f"{tab_xpath}/following-sibling::ul//li[contains(text(), 'Example Group 1')]")

        item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[contains(text(), 'Example Model')]]"
        group.find_by_xpath(item_xpath)

    def test_plugin_navbar_modify_circuits(self):
        """
        Verify that the example plugin is able to add a new group and items to an existing menu tab.
        """
        # Set test user to admin
        self.user.is_superuser = True
        self.user.save()

        # Retrieve home page
        self.browser.visit(self.live_server_url)

        tab_xpath = "//*[@id='navbar']//*[contains(text(), 'Circuits')]"
        tab = self.browser.find_by_xpath(tab_xpath)
        tab.click()
        self.assertTrue(bool(tab["aria-expanded"]))

        for group_name, items in self.navbar["Circuits"].items():
            group = tab.find_by_xpath(f"{tab_xpath}/following-sibling::ul//li[contains(text(), '{group_name}')]")
            for item_name, item_details in items.items():
                item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[contains(text(), '{item_name}')]]"
                item = group.find_by_xpath(item_xpath)

                for button_name in item_details["buttons"]:
                    button = item.find_by_xpath(f"{item_xpath}/div//a[@title='{button_name}']")
                    # Ensure button has matching class for its name
                    button_class = getattr(ButtonActionColorChoices, button_name.upper(), None)
                    if button_class:
                        self.assertIn(button_class, button["class"])
                    # Ensure button has matching icon for its name
                    button_icon = getattr(ButtonActionIconChoices, button_name.upper(), None)
                    if button_icon:
                        icon = button.find_by_xpath(f"{item_xpath}/div//a[@title='{button_name}']/i")
                        self.assertIn(button_icon, icon["class"])

    def test_plugin_navbar_plugin_tab(self):
        """
        Test that old-style plugin menu definitions are correctly rendered to the Plugins menu tab.
        """
        # Set test user to admin
        self.user.is_superuser = True
        self.user.save()

        # Retrieve home page
        self.browser.visit(self.live_server_url)

        tab_xpath = "//*[@id='navbar']//*[contains(text(), 'Plugins')]"
        tab = self.browser.find_by_xpath(tab_xpath)
        tab.click()
        self.assertTrue(bool(tab["aria-expanded"]))

        for group_name, items in self.navbar["Plugins"].items():
            group = tab.find_by_xpath(f"{tab_xpath}/following-sibling::ul//li[contains(text(), '{group_name}')]")
            for item_name, item_details in items.items():
                item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[contains(text(), '{item_name}')]]"
                item = group.find_by_xpath(item_xpath)

                for button_name in item_details["buttons"]:
                    button = item.find_by_xpath(f"{item_xpath}/div//a[@title='{button_name}']")
                    # Ensure button has matching class for its name
                    button_class = getattr(ButtonActionColorChoices, button_name.upper(), None)
                    if button_class:
                        self.assertIn(button_class, button.get_attribute("class"))
                    # Ensure button has matching icon for its name
                    button_icon = getattr(ButtonActionIconChoices, button_name.upper(), None)
                    if button_icon:
                        icon = button.find_by_xpath(f"{item_xpath}/div//a[@title='{button_name}']/i")
                        self.assertIn(button_icon, icon["class"])
