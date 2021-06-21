from unittest import skipIf

from django.conf import settings
from django.test.utils import override_settings

from nautobot.utilities.testing.integration import SeleniumTestCase
from nautobot.utilities.choices import ButtonActionColorChoices, ButtonActionIconChoices


@skipIf(
    "dummy_plugin" not in settings.PLUGINS,
    "dummy_plugin not in settings.PLUGINS",
)
class PluginNavBarTestCase(SeleniumTestCase):
    """Integration test the navigation menu."""

    fixtures = ["user-data.json"]
    navbar = {
        "Dummy Tab": {
            "Dummy Group 1": {
                "Dummy Model": {
                    "permission": "dummy_plugin.view_dummymodel",
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
            "Dummy Circuit Group": {
                "Dummy Model": {
                    "permission": "dummy_plugin.view_dummymodel",
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
            "Dummy Plugin": {
                "Models": {
                    "permission": "dummy_plugin.view_dummymodel",
                    "buttons": ["Add", "Import"],
                },
                "Other Models": {
                    "permission": "dummy_plugin.view_dummymodel",
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

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_plugin_navbar_new_tab(self):
        """
        Render navbar from home page with superuser.
        """
        # Set test user to admin
        self.user.is_superuser = True
        self.user.save()

        # Retrieve home page
        self.load_page(self.live_server_url)

        tab_xpath = f"//*[@id='navbar']//*[contains(text(), 'Dummy Tab')]"
        tab = self.selenium.find_element_by_xpath(tab_xpath)
        tab.click()
        self.assertTrue(bool(tab.get_attribute("aria-expanded")))

        group = tab.find_element_by_xpath(f"{tab_xpath}/following-sibling::ul//li[contains(text(), 'Dummy Group 1')]")

        item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[contains(text(), 'Dummy Model')]]"
        group.find_element_by_xpath(item_xpath)

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_plugin_navbar_modify_circuits(self):
        """
        Render navbar from home page with superuser.
        """
        # Set test user to admin
        self.user.is_superuser = True
        self.user.save()

        # Retrieve home page
        self.load_page(self.live_server_url)

        tab_xpath = f"//*[@id='navbar']//*[contains(text(), 'Circuits')]"
        tab = self.selenium.find_element_by_xpath(tab_xpath)
        tab.click()
        self.assertTrue(bool(tab.get_attribute("aria-expanded")))

        for group_name, items in self.navbar["Circuits"].items():
            group = tab.find_element_by_xpath(
                f"{tab_xpath}/following-sibling::ul//li[contains(text(), '{group_name}')]"
            )
            for item_name, item_details in items.items():
                item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[contains(text(), '{item_name}')]]"
                item = group.find_element_by_xpath(item_xpath)

                for button_name in item_details["buttons"]:
                    button = item.find_element_by_xpath(f"{item_xpath}/div//a[@title='{button_name}']")
                    # Ensure button has matching class for its name
                    button_class = getattr(ButtonActionColorChoices, button_name.upper(), None)
                    if button_class:
                        rendered_button_class = button.get_attribute("class").split(" ")[-1].split("-")[-1]
                        self.assertEquals(button_class, rendered_button_class)
                    # Ensure button has matching icon for its name
                    button_icon = getattr(ButtonActionIconChoices, button_name.upper(), None)
                    if button_icon:
                        icon = button.find_element_by_xpath(f"{item_xpath}/div//a[@title='{button_name}']/i")
                        rendered_button_icon = icon.get_attribute("class").split(" ")[-1]
                        self.assertEquals(button_icon, rendered_button_icon)
