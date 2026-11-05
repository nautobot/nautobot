"""The sidenav's tabs, groups and items, for the admin and for a user with one permission.

The Selenium test `test_navbar_render_with_missing_items_and_no_empty_tabs_and_groups` is not ported. It
registers a tab with an empty group through `register_menu_items` inside the server process, which a
browser test against a running instance cannot do.
"""

from playwright.sync_api import expect
import pytest

from nautobot.playwright.helpers import log_in
from nautobot.playwright.home_page import HomePage
from nautobot.playwright.nav_menu import NavMenu

# The tabs, groups and items the Selenium test checked, each item with the object type that grants it.
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

# Relationships are the only item the limited-permission user may view, so of the tabs above it sees only Extensibility.
LIMITED_OBJECT_TYPES = ("extras.relationship",)


class NavBarTestCase:
    """The sidenav shows every tab, group and item for the admin, and only the permitted ones for a limited user."""

    def test_navbar_render_superuser(self, auth_page, base_url):
        """For the admin, each tab holds its groups and items, and opening the tab displays them."""
        HomePage(auth_page, base_url).navigate()
        nav = NavMenu(auth_page)

        for tab_name, groups in NAVBAR.items():
            nav.expect_tab(tab_name)
            # The flyout is closed, so these labels are read from the DOM text; inner_text() would read them as ''.
            nav.expect_tab_collapsed(tab_name)
            for group_name, items in groups.items():
                assert group_name in nav.group_labels(tab_name), (
                    f"Tab {tab_name!r} has no group {group_name!r}. Its groups: {nav.group_labels(tab_name)}"
                )
                for item_name in items:
                    assert item_name in nav.item_labels(tab_name, group_name), (
                        f"Group {tab_name!r} > {group_name!r} has no item {item_name!r}. "
                        f"Its items: {nav.item_labels(tab_name, group_name)}"
                    )

            nav.expand_tab(tab_name)
            for group_name, items in groups.items():
                for item_name in items:
                    expect(nav.item_link(tab_name, group_name, item_name)).to_be_visible()
            nav.collapse_tab(tab_name)

    @pytest.mark.behavioral
    # storage_state=None drops the admin's session login, so the test can log in as its own user.
    @pytest.mark.browser_context_args(storage_state=None)
    def test_navbar_render_with_limited_permissions(self, page, base_url, created_view_only_user):
        """A user who can view only relationships gets the Extensibility tab with Relationships and no Organization tab."""
        user = created_view_only_user(*LIMITED_OBJECT_TYPES)
        log_in(page, user["username"], user["password"])
        HomePage(page, base_url).navigate()
        nav = NavMenu(page)

        for tab_name, groups in NAVBAR.items():
            granted = {
                item_name: object_type in LIMITED_OBJECT_TYPES
                for items in groups.values()
                for item_name, object_type in items.items()
            }
            if not any(granted.values()):
                nav.expect_no_tab(tab_name)
                continue
            nav.expect_tab(tab_name)
            for group_name, items in groups.items():
                item_labels = nav.item_labels(tab_name, group_name)
                for item_name in items:
                    assert (item_name in item_labels) == granted[item_name], (
                        f"Item {tab_name!r} > {group_name!r} > {item_name!r} should "
                        f"{'' if granted[item_name] else 'not '}be shown. Items shown: {item_labels}"
                    )
