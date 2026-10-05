"""Shared page object for detail views built with the UI component framework.

These views share one heading, the Edit button, and the same card markup for
every panel. Subclasses set DETAIL_PATH and VERBOSE_NAME and add locators
specific to their model.

    class DeviceDetailPage(DetailPage):
        DETAIL_PATH = "/dcim/devices/{pk}/"
        VERBOSE_NAME = "Device"
"""

import re

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


class DetailPage(BasePage):
    """Navigation, heading, Edit button and deferred-component helpers for detail views."""

    DETAIL_PATH = ""  # REQUIRED in subclass, e.g. "/dcim/devices/{pk}/"
    VERBOSE_NAME = ""  # REQUIRED in subclass, e.g. "Device". The Edit button reads "Edit <this>".

    # The span inside the h1. Reading the h1 appends the copy button's label to the name.
    _HEADING = "#page-title #copy_title"
    _EDIT_BUTTON = "#edit-button"
    # Removed when the deferred content swaps in. The spinner is an htmx-indicator at opacity 0,
    # which Playwright still counts as visible, so assert the count.
    _PLACEHOLDER_SPINNER = "[hx-trigger='load'][hx-select^='#component-'] .spinner-border"
    # The placeholder's follow-up request.
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
    # Deferred components
    # -------------------------------------------------------------------------

    def fail_deferred_components(self, status=500):
        """Make every deferred component's follow-up request fail, so each placeholder stays on the page."""
        self.page.route(self._DEFERRED_COMPONENT_REQUEST, lambda route: route.fulfill(status=status, body=""))

    def allow_deferred_components(self):
        """Undo fail_deferred_components()."""
        self.page.unroute(self._DEFERRED_COMPONENT_REQUEST)

    def expect_deferred_placeholder_count(self, expected):
        """Assert (auto-retrying) that *expected* deferred components are still showing a placeholder."""
        expect(self.page.locator(self._PLACEHOLDER_SPINNER)).to_have_count(expected)
