from nautobot.core.testing.integration import SeleniumTestCase


class NavBarTestCase(SeleniumTestCase):
    """Integration test the navigation menu."""

    navbar = {
        "Organization": {
            "Locations": {
                "Locations": {
                    "permission": "dcim.view_location",
                    "buttons": ["Add"],
                },
                "Location Types": {
                    "permission": "dcim.view_locationtype",
                    "buttons": ["Add"],
                },
            },
            "Tags": {
                "Tags": {
                    "permission": "extras.view_tag",
                    "buttons": ["Add"],
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
            tab_xpath = f"//*[@id='navbar']//span[normalize-space()='{tab_name}']/.."
            tab = self.browser.find_by_xpath(tab_xpath)
            tab.click()
            self.assertEqual(tab["aria-expanded"], "true")

            for group_name, items in groups.items():
                # Append onto tab xpath with group name search
                group = tab.find_by_xpath(f"{tab_xpath}/following-sibling::ul//li[normalize-space()='{group_name}']")

                for item_name in items:
                    item_xpath = f"{tab_xpath}/following-sibling::ul//li[.//a[normalize-space()='{item_name}']]"
                    group.find_by_xpath(item_xpath)

            tab.click()

    def test_navbar_render_with_limited_permissions(self):
        """
        Render navbar from home page with limited permissions.
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
            tabs = self.browser.find_by_xpath(f"//*[@id='navbar']//span[normalize-space()='{tab_name}']/..")
            if tab_flag:
                self.assertEqual(len(tabs), 1)
            else:
                self.assertEqual(len(tabs), 0)
