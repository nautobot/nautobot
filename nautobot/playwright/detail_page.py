"""Shared page object for Nautobot object detail views.

The UI component framework builds every detail view (device, location, prefix, ...) from
the same pieces: one heading, the standard action buttons, and a set of panels that all
render the same card markup. That shared behavior lives here, so a markup change is a
single edit. Subclasses set `DETAIL_PATH` and `VERBOSE_NAME` and add only what is
specific to their model:

    class DeviceDetailPage(DetailPage):
        DETAIL_PATH = "/dcim/devices/{pk}/"
        VERBOSE_NAME = "Device"
"""

import re

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


class DetailPage(BasePage):
    """Shared detail-view behavior: navigation, the heading, the Edit button, and panels.

    `VERBOSE_NAME` names the model, which core uses to label the Edit button
    "Edit <verbose name>".

    The selectors, which are not obvious from their values:

    - `_HEADING` is the heading's own span, not the surrounding h1. The h1 also holds the
      copy-to-clipboard button, whose label would come back as part of the object's name.
    - `_PANEL_TITLE` is the single `strong` in a panel header, holding that panel's title.
      Titles are matched without regard to case: a panel's own label is uppercased when it
      is rendered ("MANAGEMENT"), while a table panel's title keeps the case it was
      declared with ("Assigned VRFs").
    - `_ENCLOSING_CARD` walks from a panel title to the card that owns it. Its predicate
      matches a whole class name because a `contains` match stops at the `card-header` in
      between and returns the header.
    - `_PLACEHOLDER_SPINNER` and `_DEFERRED_COMPONENT_REQUEST` are the two halves of
      deferred rendering. A component with `deferred_render` set ships a placeholder card
      with a spinner in its body, then fetches its real body with a second request to the
      same URL carrying the component's id. The spinner lives inside the placeholder, so
      it is gone once that body has swapped in. Count it by presence rather than
      visibility, since htmx keeps `.htmx-indicator` transparent except while its own
      request is in flight.
    """

    DETAIL_PATH = ""  # REQUIRED in subclass, e.g. "/dcim/devices/{pk}/"
    VERBOSE_NAME = ""  # REQUIRED in subclass, e.g. "Device"

    _HEADING = "#page-title #copy_title"
    _EDIT_BUTTON = "#edit-button"
    _PANEL_TITLE = ".card > .card-header strong"
    _ENCLOSING_CARD = "xpath=ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' card ')][1]"
    _PLACEHOLDER_SPINNER = "[hx-trigger='load'][hx-select^='#component-'] .spinner-border"
    _DEFERRED_COMPONENT_REQUEST = re.compile(r"[?&]component_id=")

    def __init__(self, page, base_url):
        """Fail fast on a subclass that forgot to set `DETAIL_PATH` or `VERBOSE_NAME`."""
        if not self.DETAIL_PATH:
            raise ValueError(f"{type(self).__name__} must set DETAIL_PATH (e.g. '/dcim/devices/{{pk}}/').")
        if not self.VERBOSE_NAME:
            raise ValueError(f"{type(self).__name__} must set VERBOSE_NAME (e.g. 'Device').")
        super().__init__(page, base_url)

    # -------------------------------------------------------------------------
    # Navigation, heading and standard buttons
    # -------------------------------------------------------------------------

    def navigate(self, pk):
        """Go to the detail view of the object with primary key *pk*."""
        self._goto(self.DETAIL_PATH.format(pk=pk))

    def expect_heading(self, name):
        """Assert (auto-retrying) that the page heading is *name*."""
        expect(self.page.locator(self._HEADING)).to_have_text(name)

    def expect_edit_button(self):
        """Assert (auto-retrying) that this model's Edit button is rendered."""
        expect(self.page.locator(self._EDIT_BUTTON)).to_contain_text(f"Edit {self.VERBOSE_NAME}")

    # -------------------------------------------------------------------------
    # Panels
    # -------------------------------------------------------------------------

    def panel(self, title):
        """Locator for the panel card titled *title*, matched without regard to case."""
        heading = self.page.locator(self._PANEL_TITLE).filter(
            has_text=re.compile(rf"^\s*{re.escape(title)}\s*$", re.IGNORECASE)
        )
        return heading.locator(self._ENCLOSING_CARD)

    def expect_panel(self, title):
        """Assert (auto-retrying) that exactly one panel on the page is titled *title*."""
        expect(self.panel(title)).to_have_count(1)

    def expect_no_panel(self, title):
        """Assert (auto-retrying) that no panel on the page is titled *title*."""
        expect(self.panel(title)).to_have_count(0)

    def expect_panel_to_contain(self, title, text):
        """Assert (auto-retrying) that the panel titled *title* shows *text*, scoped to that one card."""
        expect(self.panel(title)).to_contain_text(text)

    def expect_panel_field(self, title, key, value):
        """Assert (auto-retrying) that the row keyed *key* in panel *title* contains *value*."""
        row = self.panel(title).locator("tr").filter(has=self.page.locator(f"td:first-child:text-is({key!r})"))
        expect(row.locator("td").nth(1)).to_contain_text(value)

    # -------------------------------------------------------------------------
    # Deferred components
    # -------------------------------------------------------------------------

    def fail_deferred_components(self, status=500):
        """Make every deferred component's follow-up request fail, leaving its placeholder unresolved."""
        self.page.route(self._DEFERRED_COMPONENT_REQUEST, lambda route: route.fulfill(status=status, body=""))

    def allow_deferred_components(self):
        """Stop failing deferred components' follow-up requests."""
        self.page.unroute(self._DEFERRED_COMPONENT_REQUEST)

    def expect_deferred_placeholder_count(self, expected):
        """Assert (auto-retrying) that *expected* deferred components are still showing a placeholder."""
        expect(self.page.locator(self._PLACEHOLDER_SPINNER)).to_have_count(expected)
