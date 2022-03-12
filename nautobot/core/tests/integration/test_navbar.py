from django.test.utils import override_settings

from nautobot.utilities.choices import ButtonActionColorChoices, ButtonActionIconChoices
from nautobot.utilities.testing.integration import SeleniumTestCase


class NavBarTestCase(SeleniumTestCase):
    """Integration test the navigation menu."""

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

    def setUp(self):
        super().setUp()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_navbar_render_superuser(self):
        """
        Render navbar from home page with superuser.
        """
        # Set test user to admin
        self.user.is_superuser = True
        self.user.save()

        # Retrieve home page
        self.browser.visit(self.live_server_url)

        for tab_name, groups in self.navbar.items():
            # XPath to find tabs using the tab name
            tab_xpath = f"//*[@id='navbar']//*[contains(text(), '{tab_name}')]"
            tab = self.browser.find_by_xpath(tab_xpath)
            tab.click()
            self.assertTrue(bool(tab["aria-expanded"]))

            for group_name, items in groups.items():
                # Append onto tab xpath with group name search
                group = tab.find_by_xpath(f"{tab_xpath}/following-sibling::ul//li[contains(text(), '{group_name}')]")

                for item_name, item_details in items.items():
                    item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[contains(text(), '{item_name}')]]"
                    item = group.find_by_xpath(item_xpath)

                    for button_name in item_details["buttons"]:
                        button = item.find_by_xpath(f"{item_xpath}/div//a[@title='{button_name}']")
                        # Ensure button has matching class for its name
                        button_class = getattr(ButtonActionColorChoices, button_name.upper(), None)
                        if button_class:
                            rendered_button_class = button["class"].split(" ")[-1].split("-")[-1]
                            self.assertEqual(button_class, rendered_button_class)
                        # Ensure button has matching icon for its name
                        button_icon = getattr(ButtonActionIconChoices, button_name.upper(), None)
                        if button_icon:
                            icon = button.find_by_xpath(f"{item_xpath}/div//a[@title='{button_name}']/i")
                            rendered_button_icon = icon["class"].split(" ")[-1]
                            self.assertEqual(button_icon, rendered_button_icon)

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_navbar_render_limit_permissions(self):
        """
        Render navbar from home page with limited permissions.
        """
        self.add_permissions("dcim.view_site")
        self.add_permissions("extras.view_relationship")
        user_permissions = self.user.get_all_permissions()

        self.browser.visit(self.live_server_url)

        for tab_name, groups in self.navbar.items():
            # XPath to find tabs using the tab name
            tab_xpath = f"//*[@id='navbar']//*[contains(text(), '{tab_name}')]"
            tab = self.browser.find_by_xpath(tab_xpath)
            tab.click()
            self.assertTrue(bool(tab["aria-expanded"]))

            for group_name, items in groups.items():
                # Append onto tab xpath with group name search
                group = tab.find_by_xpath(f"{tab_xpath}/following-sibling::ul//li[contains(text(), '{group_name}')]")

                for item_name, item_details in items.items():
                    item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[contains(text(), '{item_name}')]]"
                    item = group.find_by_xpath(item_xpath)
                    if item_details["permission"] in user_permissions:
                        self.assertNotEqual(item["class"], "disabled", f"Item `{item_name}` should not be disabled.")
                    else:
                        self.assertEqual(item["class"], "disabled", f"Item `{item_name}` should be disabled.")

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_navbar_render_no_permissions(self):
        """
        Render navbar from home page with no permissions.
        """
        self.browser.visit(self.live_server_url)

        for tab_name, groups in self.navbar.items():
            # XPath to find tabs using the tab name
            tab_xpath = f"//*[@id='navbar']//*[contains(text(), '{tab_name}')]"
            tab = self.browser.find_by_xpath(tab_xpath)
            tab.click()
            self.assertTrue(bool(tab["aria-expanded"]))

            for group_name, items in groups.items():
                # Append onto tab xpath with group name search
                group = tab.find_by_xpath(f"{tab_xpath}/following-sibling::ul//li[contains(text(), '{group_name}')]")

                for item_name, _ in items.items():
                    item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[contains(text(), '{item_name}')]]"
                    item = group.find_by_xpath(item_xpath)
                    self.assertEqual(item["class"], "disabled", f"Item `{item_name}` should be disabled.")

    @override_settings(HIDE_RESTRICTED_UI=True)
    def test_navbar_render_restricted_ui(self):
        """
        Render navbar from home page with restricted UI set to True.
        This restricts the user to be able to view ONLY relationships on the navbar.
        It then checks the UI for these restrictions.
        """

        self.add_permissions("extras.view_relationship")
        user_permissions = self.user.get_all_permissions()

        self.browser.visit(self.live_server_url)

        for tab_name, groups in self.navbar.items():
            tab_flag = False
            for _, items in groups.items():
                for _, item_details in items.items():
                    if item_details["permission"] in user_permissions:
                        tab_flag = True

            # XPath to find tabs using the tab name
            tabs = self.browser.find_by_xpath(f"//*[@id='navbar']//*[contains(text(), '{tab_name}')]")
            if tab_flag:
                self.assertEqual(len(tabs), 1)
            else:
                self.assertEqual(len(tabs), 0)
