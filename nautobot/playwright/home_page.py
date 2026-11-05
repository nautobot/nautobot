"""Shared page object for the home page (/).

The home page is a grid of panels, one card per panel, laid out in columns the user can reorder by
dragging. Each panel lists items, and an item the user can view shows a count badge and a link to
that model's list view. Panel and item names are the rendered text from each app's `homepage.py`.

The server leaves out every panel and item the user has no permission for, so an absent panel is
missing from the DOM, not hidden. A collapsed panel is in the DOM but not displayed, so read text
with `text_content()` (never `inner_text()`, which returns '' for anything not displayed) and assert
presence with counts rather than visibility, unless the test is about collapsing.
"""

import re

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


def _exact(text):
    """Regex that matches *text* as the whole of an element's text, ignoring surrounding whitespace."""
    return re.compile(rf"^\s*{re.escape(text)}\s*$")


class HomePage(BasePage):
    """The home page panel grid: panels, their items and counters, and collapsing a panel."""

    PATH = "/"
    # Nautobot's HOMEPAGE_PANELS_LAYOUT_COLUMNS. A literal, because importing nautobot.core needs a Django config.
    COLUMN_COUNT = 4

    _PANELS = "#draggable-homepage-panels"
    _COLUMN = "#draggable-homepage-panels > .nb-panel-group"
    # Overrides BasePage's panel title, so the inherited panel(), expect_panel(), expect_no_panel() and
    # expect_panel_to_contain() find home page panels, whose name is the card header's <h2>.
    _PANEL_TITLE = "#draggable-homepage-panels .card > .card-header > h2"
    # One <li> per item. A grouped item ("Connections") holds one link per member, each in its own <p>.
    _ITEM = "li.list-group-item"
    # The count badge is a direct child of a top-level item's <li>. A locked item shows a padlock instead.
    _ITEM_BADGE = ":scope > span.badge"
    _ENCLOSING_ITEM = "xpath=ancestor::li[contains(concat(' ', normalize-space(@class), ' '), ' list-group-item ')][1]"
    # A <span role="button"> in the card header; Bootstrap toggles the panel's <ul> and its `aria-expanded`.
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

    def expect_columns(self):
        """Assert (auto-retrying) that the grid has its fixed number of columns, which the server always renders."""
        expect(self.page.locator(self._COLUMN)).to_have_count(self.COLUMN_COUNT)

    # -------------------------------------------------------------------------
    # Panels
    # -------------------------------------------------------------------------

    def panel_names(self):
        """Return the name of every rendered panel, in DOM order (column by column)."""
        return [(title.text_content() or "").strip() for title in self.page.locator(self._PANEL_TITLE).all()]

    # -------------------------------------------------------------------------
    # Items
    # -------------------------------------------------------------------------

    def item_link(self, panel_name, item_name):
        """Locator for the link named exactly *item_name* in the panel *panel_name*."""
        return self.panel(panel_name).locator(f"{self._ITEM} a").filter(has_text=_exact(item_name))

    def expect_item(self, panel_name, item_name, href=None):
        """Assert (auto-retrying) that panel *panel_name* has exactly one *item_name* link, pointing at *href* if given."""
        link = self.item_link(panel_name, item_name)
        expect(link).to_have_count(1)
        if href is not None:
            expect(link).to_have_attribute("href", href)

    def expect_no_item(self, panel_name, item_name):
        """Assert (auto-retrying) that panel *panel_name* has no *item_name* link."""
        expect(self.item_link(panel_name, item_name)).to_have_count(0)

    def item_count(self, panel_name, item_name):
        """Return the count badge of the top-level item *item_name* in panel *panel_name*, as an int.

        The badge uses a thousands separator ("1,210"), which is removed before parsing. Fails, rather than
        returning a number, when the badge is a padlock: the user holds only some of the item's permissions.
        A grouped item's members ("Connections" > "Cables") each have their own badge, which this does not read.
        """
        link = self.item_link(panel_name, item_name)
        expect(link).to_have_count(1)
        badge = link.locator(self._ENCLOSING_ITEM).locator(self._ITEM_BADGE)
        expect(badge).to_have_count(1)
        text = (badge.text_content() or "").strip()
        digits = text.replace(",", "")
        assert digits.isdigit(), f"The {item_name!r} counter in panel {panel_name!r} is not a number: {text!r}"
        return int(digits)

    # -------------------------------------------------------------------------
    # Collapsing
    # -------------------------------------------------------------------------

    def toggle_panel(self, panel_name):
        """Click the collapse toggle of panel *panel_name* and wait until its new state is saved.

        The page saves the layout to the user's config after every toggle. A reload before that request
        finishes would render the old state, so this waits for the response and fails if it is an error.
        """
        with self.page.expect_response(
            lambda response: response.request.method == "PATCH" and response.url.endswith(self._USER_CONFIG_API)
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
