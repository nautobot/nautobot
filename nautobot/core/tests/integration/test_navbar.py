from django.contrib.auth.models import Permission

from nautobot.users.models import User
from nautobot.utilities.testing.integration import SeleniumTestCase
from nautobot.utilities.choices import ButtonActionColorChoices, ButtonActionIconChoices


class NavBarTestCase(SeleniumTestCase):
    """Integration test the naviagation menu."""

    fixtures = ["user-data.json"]
    navbar = {
        "Organization": {
            "Sites": {
                "Sites": {
                    "permission": "dcim.view_site",
                    "buttons": ["Add", "Import"],
                },
                "Regions": {
                    "permission": "dcim.view_region",
                    "buttons": ["Add", "Import"],
                },
            },
            "Tags": {
                "Tags": {
                    "permission": "extras.view_tag",
                    "buttons": ["Add", "Import"],
                },
            },
        },
        "Extensibility": {
            "Data Management": {
                "Relationships": {
                    "permission": "extras.view_relationship",
                    "buttons": [
                        "Add",
                    ],
                },
            },
        },
    }

    def test_navbar_render_superuser(self):
        """
        Render navbar from home page with superuser.
        """

        # Login
        self.login("bob", "bob")
        # Retrieve home page
        self.selenium.get(f"{self.live_server_url}")
        self.selenium.wait_for_html("body")

        for tab_name, groups in self.navbar.items():
            # XPath to find tabs using the tab name
            tab_xpath = f"//*[@id='navbar']//*[contains(text(), '{tab_name}')]"
            tab = self.selenium.find_element_by_xpath(tab_xpath)
            tab.click()
            self.assertTrue(bool(tab.get_attribute("aria-expanded")))

            for group_name, items in groups.items():
                # Append onto tab xpath with group name search
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

    def test_navbar_render_limit_permissions(self):
        """
        Render navbar from home page with limited permissions.
        """
        user = User.objects.get(username="alice")
        user.user_permissions.add(Permission.objects.get(codename="view_site"))
        user.user_permissions.add(Permission.objects.get(codename="view_relationship"))
        user_permissions = user.get_user_permissions()
        self.login("alice", "bob")
        self.selenium.get(f"{self.live_server_url}")
        self.selenium.wait_for_html("body")

        for tab_name, groups in self.navbar.items():
            # XPath to find tabs using the tab name
            tab_xpath = f"//*[@id='navbar']//*[contains(text(), '{tab_name}')]"
            tab = self.selenium.find_element_by_xpath(tab_xpath)
            tab.click()
            self.assertTrue(bool(tab.get_attribute("aria-expanded")))

            for group_name, items in groups.items():
                # Append onto tab xpath with group name search
                group = tab.find_element_by_xpath(
                    f"{tab_xpath}/following-sibling::ul//li[contains(text(), '{group_name}')]"
                )

                for item_name, item_details in items.items():
                    item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[contains(text(), '{item_name}')]]"
                    item = group.find_element_by_xpath(item_xpath)
                    if item_details["permission"] in user_permissions:
                        self.assertNotEquals(
                            item.get_attribute("class"), "disabled", f"Item `{item_name}` should not be disabled."
                        )
                    else:
                        self.assertEquals(
                            item.get_attribute("class"), "disabled", f"Item `{item_name}` should be disabled."
                        )

    def test_navbar_render_no_permissions(self):
        """
        Render navbar from home page with no permissions.
        """
        self.login("charlie", "bob")
        self.selenium.get(f"{self.live_server_url}")
        self.selenium.wait_for_html("body")

        for tab_name, groups in self.navbar.items():
            # XPath to find tabs using the tab name
            tab_xpath = f"//*[@id='navbar']//*[contains(text(), '{tab_name}')]"
            tab = self.selenium.find_element_by_xpath(tab_xpath)
            tab.click()
            self.assertTrue(bool(tab.get_attribute("aria-expanded")))

            for group_name, items in groups.items():
                # Append onto tab xpath with group name search
                group = tab.find_element_by_xpath(
                    f"{tab_xpath}/following-sibling::ul//li[contains(text(), '{group_name}')]"
                )

                for item_name, _ in items.items():
                    item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[contains(text(), '{item_name}')]]"
                    item = group.find_element_by_xpath(item_xpath)
                    self.assertEquals(item.get_attribute("class"), "disabled", f"Item `{item_name}` should be disabled.")
