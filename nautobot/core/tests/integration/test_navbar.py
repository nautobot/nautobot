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
            "Metadata": {
                "Tags": {
                    "permission": "extras.view_tag",
                    "buttons": ["Add"],
                },
            },
        },
        "Extensibility": {
            "Data Model": {
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
            sidenav_section = self.find_sidenav_section(tab_name)
            sidenav_section.button.click()

            self.assertTrue(sidenav_section.is_expanded)

            for group_name, items in groups.items():
                # Append onto tab xpath with group name search
                group = sidenav_section.flyout.find_by_xpath(
                    f"//li[@class='nb-sidenav-link-group' and normalize-space()='{group_name}']"
                )

                for item_name in items:
                    item_xpath = f"//a[@class='nb-sidenav-link' and normalize-space()='{item_name}']"
                    group.find_by_xpath(item_xpath)

            sidenav_section.button.click()

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
            tabs = self.browser.find_by_xpath(f"//*[@id='sidenav']//li[@data-section-name='{tab_name}']")
            if tab_flag:
                self.assertEqual(len(tabs), 1, msg=f'"{tab_name}" was unexpectedly not found.')
            else:
                self.assertTrue(tabs.is_empty(), msg=f'"{tab_name}" was unexpectedly found.')

    def test_navbar_render_with_limited_permissions_and_no_empty_tabs_and_groups(self):
        """
        Render navbar from home page with limited permissions.
        This restricts the user to be able to view ONLY locations on the navbar.
        It then checks the UI for these restrictions and asserts that tabs and groups with no children are not rendered.
        """

        self.add_permissions("dcim.view_location")
        user_permissions = self.user.get_all_permissions()

        self.browser.visit(self.live_server_url)

        visible_tabs = set()
        visible_groups = set()
        visible_items = set()

        for tab_name, groups in self.navbar.items():
            for group_name, items in groups.items():
                for item_name, item_details in items.items():
                    if item_details["permission"] in user_permissions:
                        visible_tabs.add(tab_name)
                        visible_groups.add(group_name)
                        visible_items.add(item_name)
                    item = self.browser.find_by_xpath(
                        f"//*[@id='sidenav']//a[@data-item-weight and normalize-space()='{item_name}']"
                    )
                    self.assertEqual(len(item), 1 if item_name in visible_items else 0)
                group = self.browser.find_by_xpath(
                    f"//*[@id='sidenav']//li[@data-group-weight and normalize-space()='{group_name}']"
                )
                self.assertEqual(len(group), 1 if group_name in visible_groups else 0)
            tab = self.browser.find_by_xpath(f"//*[@id='sidenav']//li[@data-section-name='{tab_name}']")
            self.assertEqual(len(tab), 1 if tab_name in visible_tabs else 0)
