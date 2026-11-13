"""The home page panel grid: panels, items, counters, permissions and collapsing."""

import pytest

from nautobot.playwright.helpers import log_in
from nautobot.playwright.home_page import HomePage

# The panels and items that the Selenium test checked, keyed by the names that the home page displays (as
# defined in each app's `homepage.py`). Each item has two values. `object_type` is the type that the
# limited user is given view permission on. `path` is the item's list view, which is the href of the item's
# link; with `/api` in front, the same path is the item's REST endpoint.
LAYOUT = {
    "Organization": {
        "Locations": {"object_type": "dcim.location", "path": "/dcim/locations/"},
        "Tenants": {"object_type": "tenancy.tenant", "path": "/tenancy/tenants/"},
    },
    "Power": {
        "Power Feeds": {"object_type": "dcim.powerfeed", "path": "/dcim/power-feeds/"},
        "Power Panels": {"object_type": "dcim.powerpanel", "path": "/dcim/power-panels/"},
    },
    "Circuits": {
        "Providers": {"object_type": "circuits.provider", "path": "/circuits/providers/"},
        "Circuits": {"object_type": "circuits.circuit", "path": "/circuits/circuits/"},
    },
}

# What the limited-permission user may view: one item each in Organization and Circuits, nothing in Power.
LIMITED_OBJECT_TYPES = ("dcim.location", "circuits.circuit")


class HomeTestCase:
    """The home page shows the panels and items the user may view, with correct counts, and remembers collapsed panels."""

    def test_homepage_render(self, auth_page, base_url):
        """For the admin, the grid has its columns, and every panel shows each of its items linking to its list view."""
        home = HomePage(auth_page, base_url)
        home.navigate()
        home.expect_loaded()
        home.expect_columns()

        for panel_name, items in LAYOUT.items():
            home.expect_panel(panel_name)
            for item_name, item in items.items():
                home.expect_item(panel_name, item_name, href=item["path"])

    @pytest.mark.behavioral
    def test_homepage_render_counters(self, auth_page, base_url, api_count):
        """Each item's counter equals the REST API count for the admin, who can view every object."""
        home = HomePage(auth_page, base_url)
        home.navigate()

        mismatches = {}
        for panel_name, items in LAYOUT.items():
            for item_name, item in items.items():
                shown = home.item_count(panel_name, item_name)
                expected = api_count(item["path"].lstrip("/"))
                if shown != expected:
                    mismatches[f"{panel_name} > {item_name}"] = f"page shows {shown}, API counts {expected}"
        assert not mismatches, f"Home page counters disagree with the API: {mismatches}"

    @pytest.mark.behavioral
    # storage_state=None starts the browser context without the admin's saved login, so the test can log in as its own user.
    @pytest.mark.browser_context_args(storage_state=None)
    def test_homepage_render_with_limit_permissions(self, page, base_url, created_view_only_user):
        """A user who can view only locations and circuits sees only those items, and no panel without one."""
        user = created_view_only_user(*LIMITED_OBJECT_TYPES)
        log_in(page, user["username"], user["password"])
        home = HomePage(page, base_url)
        home.navigate()
        home.expect_loaded()

        for panel_name, items in LAYOUT.items():
            if not any(item["object_type"] in LIMITED_OBJECT_TYPES for item in items.values()):
                home.expect_no_panel(panel_name)
                continue
            home.expect_panel(panel_name)
            for item_name, item in items.items():
                if item["object_type"] in LIMITED_OBJECT_TYPES:
                    home.expect_item(panel_name, item_name, href=item["path"])
                else:
                    home.expect_no_item(panel_name, item_name)

    @pytest.mark.behavioral
    def test_homepage_layout_panels_collapse(self, auth_page, base_url, default_homepage_layout):
        """A collapsed panel stays collapsed after a reload, because its state is saved to the user's config.

        `default_homepage_layout` starts the admin with every panel expanded and restores the admin's saved
        layout afterwards, even if an assertion fails, so the collapsed panel does not affect other tests.
        """
        home = HomePage(auth_page, base_url)
        home.navigate()
        home.expect_panel_expanded("Organization")
        home.expect_panel_expanded("Circuits")

        home.toggle_panel("Circuits")
        home.expect_panel_collapsed("Circuits")

        home.navigate()
        home.expect_panel_expanded("Organization")
        home.expect_panel_collapsed("Circuits")
