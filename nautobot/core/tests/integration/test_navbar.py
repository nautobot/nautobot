"""The sidenav's tabs, groups and items, for the admin and for a user with one permission."""

from playwright.sync_api import expect
import pytest

from nautobot.playwright.helpers import log_in
from nautobot.playwright.home_page import HomePage
from nautobot.playwright.nav_menu import NavMenu

# The tabs, groups and items under test. Each item maps to the object type whose view
# permission makes the item visible.
# "Metadata" is also a group in Extensibility, which is why groups are always looked up within their tab.
NAVBAR = {
    "Organization": {
        "Locations": {"Locations": "dcim.location", "Location Types": "dcim.locationtype"},
        "Metadata": {"Tags": "extras.tag"},
    },
    "Extensibility": {
        "Data Model": {"Relationships": "extras.relationship"},
    },
}

# The limited-permission user may view only Relationships, so Extensibility is the only tab in NAVBAR that this user sees.
LIMITED_OBJECT_TYPES = ("extras.relationship",)


class NavBarTestCase:
    """The sidenav shows every tab, group and item for the admin, and only the permitted tabs for a limited user."""

    def test_navbar_render_superuser(self, auth_page, base_url):
        """For the admin, each tab contains its groups and items, and opening the tab displays them."""
        HomePage(auth_page, base_url).navigate()
        nav = NavMenu(auth_page)

        for tab_name, groups in NAVBAR.items():
            nav.expect_tab(tab_name)
            nav.expect_tab_collapsed(tab_name)
            for group_name, items in groups.items():
                nav.expect_group(tab_name, group_name)
                for item_name in items:
                    nav.expect_item(tab_name, group_name, item_name)

            nav.expand_tab(tab_name)
            for group_name, items in groups.items():
                for item_name in items:
                    expect(nav.item_link(tab_name, group_name, item_name)).to_be_visible()
            nav.collapse_tab(tab_name)

    @pytest.mark.behavioral
    # storage_state=None starts the browser context without the admin's saved login, so the test can log in as its own user.
    @pytest.mark.browser_context_args(storage_state=None)
    def test_navbar_render_with_limited_permissions(self, page, base_url, create_view_only_user):
        """A user who can view only relationships sees the Extensibility tab and no Organization tab."""
        user = create_view_only_user(*LIMITED_OBJECT_TYPES)
        log_in(page, user["username"], user["password"])
        HomePage(page, base_url).navigate()
        nav = NavMenu(page)

        for tab_name, groups in NAVBAR.items():
            if any(object_type in LIMITED_OBJECT_TYPES for items in groups.values() for object_type in items.values()):
                nav.expect_tab(tab_name)
            else:
                nav.expect_no_tab(tab_name)
