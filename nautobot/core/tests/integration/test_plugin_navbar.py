from unittest import skipIf

from django.conf import settings

from nautobot.core.choices import ButtonActionColorChoices, ButtonActionIconChoices
from nautobot.core.testing.integration import SeleniumTestCase


@skipIf(
    "example_plugin" not in settings.PLUGINS,
    "example_plugin not in settings.PLUGINS",
)
class PluginNavBarTestCase(SeleniumTestCase):
    """Integration test the navigation menu."""

    fixtures = ["user-data.json"]
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
        "Plugins": {
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

        tab_xpath = "//*[@id='navbar']//span[normalize-space()='Example Menu']/.."
        tab = self.browser.find_by_xpath(tab_xpath)
        tab.click()
        self.assertTrue(bool(tab["aria-expanded"]))

        group = tab.find_by_xpath(f"{tab_xpath}/following-sibling::ul//li[normalize-space()='Example Group 1']")

        item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[normalize-space()='Example Models']]"
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

        tab_xpath = "//*[@id='navbar']//*[normalize-space()='Circuits']"
        tab = self.browser.find_by_xpath(tab_xpath)
        tab.click()
        self.assertTrue(bool(tab["aria-expanded"]))

        for group_name, items in self.navbar["Circuits"].items():
            group = tab.find_by_xpath(f"{tab_xpath}/following-sibling::ul//li[normalize-space()='{group_name}']")
            for item_name, item_details in items.items():
                item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[normalize-space()='{item_name}']]"
                item = group.find_by_xpath(item_xpath)

                for button_name in item_details["buttons"]:
                    button = item.find_by_xpath(f"{item_xpath}/div//a[@data-original-title='{button_name}']")
                    if button_class := getattr(ButtonActionColorChoices, button_name.upper(), None):
                        self.assertIn(button_class, button["class"])
                    if button_icon := getattr(ButtonActionIconChoices, button_name.upper(), None):
                        icon = button.find_by_xpath(f"{item_xpath}/div//a[@data-original-title='{button_name}']/i")
                        self.assertIn(button_icon, icon["class"])

        tab.click()

    def test_plugin_navbar_plugin_tab(self):
        """
        Test that old-style plugin menu definitions are correctly rendered to the Plugins menu tab.
        """
        # Set test user to admin
        self.user.is_superuser = True
        self.user.save()

        # Retrieve home page
        self.browser.visit(self.live_server_url)

        tab_xpath = "//*[@id='navbar']//*[normalize-space()='Plugins']"
        tab = self.browser.find_by_xpath(tab_xpath)
        tab.click()
        self.assertTrue(bool(tab["aria-expanded"]))

        for group_name, items in self.navbar["Plugins"].items():
            group = tab.find_by_xpath(f"{tab_xpath}/following-sibling::ul//li[normalize-space()='{group_name}']")
            for item_name, item_details in items.items():
                item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[normalize-space()='{item_name}']]"
                item = group.find_by_xpath(item_xpath)

                for button_name in item_details["buttons"]:
                    button = item.find_by_xpath(f"{item_xpath}/div//a[@data-original-title='{button_name}']")
                    if button_class := getattr(ButtonActionColorChoices, button_name.upper(), None):
                        self.assertIn(button_class, button["class"])
                    if button_icon := getattr(ButtonActionIconChoices, button_name.upper(), None):
                        icon = button.find_by_xpath(f"{item_xpath}/div//a[@data-original-title='{button_name}']/i")
                        self.assertIn(button_icon, icon["class"])

        tab.click()
