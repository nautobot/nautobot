"""Shared page object for the home page (/), a grid of panels that list items with a count and a link.

A panel or item that the user may not view is missing from the DOM, not hidden.
"""

import re
from urllib.parse import urlparse

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage
from nautobot.playwright.helpers import exact_text


class HomePage(BasePage):
    """The home page panel grid: panels, their items and counters, and collapsing a panel."""

    PATH = "/"

    _PANELS = "#draggable-homepage-panels"
    # Replaces BasePage's _PANEL_TITLE selector, so the inherited panel(), expect_panel(), expect_no_panel() and
    # expect_panel_to_contain() find home page panels, whose name is the card header's <h2>.
    _PANEL_TITLE = "#draggable-homepage-panels .card > .card-header > h2"
    # One <li> per item. A grouped item ("Connections") contains one link per member, each in its own <p>.
    _ITEM = "li.list-group-item"
    # The count badge is a direct child of a top-level item's <li>. A locked item shows a padlock instead.
    _ITEM_BADGE = ":scope > span.badge"
    _ENCLOSING_ITEM = "xpath=ancestor::li[contains(concat(' ', normalize-space(@class), ' '), ' list-group-item ')][1]"
    # The toggle is a <span role="button"> in the card header. Clicking it makes Bootstrap show or hide the
    # panel's <ul> and update the toggle's `aria-expanded`.
    _PANEL_TOGGLE = ".card-header [data-bs-toggle='collapse']"
    _PANEL_BODY = "ul.list-group"
    # Each collapse or expand PATCHes the whole panel layout, with each panel's collapsed state, to the user's config.
    _USER_CONFIG_API = "/api/users/config/"

    def navigate(self):
        """Go to the home page."""
        self._goto(self.PATH)

    def expect_loaded(self):
        """Assert (auto-retrying) that the panel grid, which only the home page renders, is present."""
        expect(self.page.locator(self._PANELS)).to_be_attached()

    # -------------------------------------------------------------------------
    # Items
    # -------------------------------------------------------------------------

    def item_link(self, panel_name, item_name):
        """Locator for the link named exactly *item_name* in the panel *panel_name*."""
        return self.panel(panel_name).locator(f"{self._ITEM} a").filter(has_text=exact_text(item_name))

    def expect_item(self, panel_name, item_name, href=None):
        """Assert (auto-retrying) that panel *panel_name* has exactly one *item_name* link, pointing at *href* if given."""
        link = self.item_link(panel_name, item_name)
        expect(link).to_have_count(1)
        if href is not None:
            expect(link).to_have_attribute("href", href)

    def expect_no_item(self, panel_name, item_name):
        """Assert (auto-retrying) that panel *panel_name* has no *item_name* link."""
        expect(self.item_link(panel_name, item_name)).to_have_count(0)

    def item_badge(self, panel_name, item_name):
        """Locator for the count badge of the top-level item *item_name* in panel *panel_name*.

        Call it only for a top-level item. For a member of a grouped item ("Connections" > "Cables"), it matches every member's badge.
        """
        return self.item_link(panel_name, item_name).locator(self._ENCLOSING_ITEM).locator(self._ITEM_BADGE)

    def expect_item_count(self, panel_name, item_name, expected):
        """Assert (auto-retrying) that the badge of item *item_name* in panel *panel_name* shows the int *expected*.

        The template formats the count with `intcomma`, so 1210 is shown as "1,210". The assertion fails
        when the badge is a padlock, which the page shows when the user has only some of the item's permissions.
        """
        expect(self.item_link(panel_name, item_name)).to_have_count(1)
        expect(self.item_badge(panel_name, item_name)).to_have_text(f"{expected:,}")

    # -------------------------------------------------------------------------
    # Collapsing
    # -------------------------------------------------------------------------

    def toggle_panel(self, panel_name):
        """Click the collapse toggle of panel *panel_name* and wait until its new state is saved.

        The page saves the layout to the user's config after every toggle. A reload before that request
        finishes would render the old state, so this waits for the response and fails if it is an error.
        """
        with self.page.expect_response(
            lambda response: response.request.method == "PATCH" and urlparse(response.url).path == self._USER_CONFIG_API
        ) as save:
            self.panel(panel_name).locator(self._PANEL_TOGGLE).click()
        response = save.value
        assert response.ok, f"Saving the home page layout returned {response.status}: {response.text()}"

    def expect_panel_expanded(self, panel_name):
        """Assert (auto-retrying) that panel *panel_name* is expanded: its toggle says so and its list is displayed."""
        panel = self.panel(panel_name)
        expect(panel.locator(self._PANEL_TOGGLE)).to_have_attribute("aria-expanded", "true")
        expect(panel.locator(self._PANEL_BODY)).to_have_class(re.compile(r"(^|\s)show(\s|$)"))
        expect(panel.locator(self._PANEL_BODY)).to_be_visible()

    def expect_panel_collapsed(self, panel_name):
        """Assert (auto-retrying) that panel *panel_name* is collapsed: its toggle says so and its list is hidden."""
        panel = self.panel(panel_name)
        expect(panel.locator(self._PANEL_TOGGLE)).to_have_attribute("aria-expanded", "false")
        expect(panel.locator(self._PANEL_BODY)).not_to_have_class(re.compile(r"(^|\s)show(\s|$)"))
        expect(panel.locator(self._PANEL_BODY)).to_be_hidden()
