"""Page object for the Dynamic Group add, edit, and detail views (/extras/dynamic-groups/)."""

import re

from playwright.sync_api import expect

from nautobot.playwright.base_page import select2_filter_pick
from nautobot.playwright.detail_page import DetailPage


class DynamicGroupPage(DetailPage):
    """A single dynamic group: the detail view from DetailPage, plus the add form and the filter builder on the edit form.

    Creating a filter-defined group is a two-step flow: the add form takes only the name
    and content type, and the filter fields (prefixed `filter-`) render on the edit form
    once the group exists. Saving either form does not recalculate membership; that is
    left to the "Refresh Members" job button on the detail view.
    """

    DETAIL_PATH = "/extras/dynamic-groups/{pk}/"
    VERBOSE_NAME = "Dynamic Group"
    ADD_PATH = "/extras/dynamic-groups/add/"
    EDIT_PATH = "/extras/dynamic-groups/{pk}/edit/"
    # The cached-members endpoint, read by `wait_for_member_count`.
    MEMBERS_API_PATH = "/api/extras/dynamic-groups/{pk}/members/?limit=1"

    _NAME_INPUT = "input[name='name']"
    # A plain <select>, so the stable option value (e.g. "dcim.device") is selectable directly.
    _CONTENT_TYPE_SELECT = "select[name='content_type']"
    _CREATE_BUTTON = "button[name='_create']"
    _UPDATE_BUTTON = "button[name='_update']"
    _FILTER_FORM = "#filter-form"
    # The Members tab label carries a count badge, rendered only when the count is non-zero.
    _MEMBERS_TAB_BADGE = "a[role='tab'][aria-controls='members'] span.badge"
    # "Refresh Members" is a confirmation JobButton: its data-bs-target names the modal
    # (whose id embeds the JobButton pk), and the modal's submit button runs the job.
    _REFRESH_MEMBERS_BUTTON = "button[data-bs-toggle='modal']:has-text('Refresh Members')"
    _MODAL_CONFIRM_BUTTON = "button[type='submit']"
    _PK_IN_URL = re.compile(r"/extras/dynamic-groups/([0-9a-f-]{36})/")

    # -------------------------------------------------------------------------
    # Navigation
    # -------------------------------------------------------------------------

    def navigate_add(self):
        """Go to the add form."""
        self._goto(self.ADD_PATH)

    def navigate_edit(self, pk):
        """Go to the edit form of the group *pk* and wait for its filter builder."""
        self._goto(self.EDIT_PATH.format(pk=pk))
        self.page.locator(self._FILTER_FORM).wait_for(state="attached", timeout=15_000)

    # -------------------------------------------------------------------------
    # Add and edit forms
    # -------------------------------------------------------------------------

    def create(self, name, content_type):
        """Fill and submit the add form, returning the new group's pk from the detail-view redirect."""
        self.page.fill(self._NAME_INPUT, name)
        self.page.locator(self._CONTENT_TYPE_SELECT).select_option(value=content_type)
        self._click_and_wait_for_navigation(self._CREATE_BUTTON)
        match = self._PK_IN_URL.search(self.current_url())
        assert match, f"Creating the group did not redirect to its detail view (now on {self.current_url()})."
        return match.group(1)

    def add_filter_value(self, field_name, value):
        """Add *value* to the edit form's multi-value filter field *field_name* (e.g. "location").

        Matched as a substring: location options render their full ancestry path.
        """
        select2_filter_pick(self.page, f"filter-{field_name}", search=value, pick_text=value, exact=False)
        expect(self.page.locator(f"select[name='filter-{field_name}'] option:checked", has_text=value)).to_have_count(1)

    def save(self):
        """Submit the edit form and wait for the redirect to the detail view."""
        self._click_and_wait_for_navigation(self._UPDATE_BUTTON)

    # -------------------------------------------------------------------------
    # Members
    # -------------------------------------------------------------------------

    def expect_member_count(self, expected):
        """Assert (auto-retrying) that the Members tab label shows *expected* members."""
        badge = self.page.locator(self._MEMBERS_TAB_BADGE)
        if expected:
            expect(badge).to_have_text(str(expected))
        else:
            expect(badge).to_have_count(0)

    def refresh_members(self):
        """Click "Refresh Members", confirm in its modal, and wait for the redirect back.

        This only enqueues the refresh job; use `wait_for_member_count` before asserting
        on the new membership.
        """
        button = self.page.locator(self._REFRESH_MEMBERS_BUTTON).first
        modal = button.get_attribute("data-bs-target", timeout=10_000)
        assert modal, "The Refresh Members button names no confirmation modal."
        button.click()
        confirm = f"{modal} {self._MODAL_CONFIRM_BUTTON}"
        self.page.locator(confirm).wait_for(state="visible", timeout=10_000)
        self._click_and_wait_for_navigation(confirm)

    def wait_for_member_count(self, pk, expected, timeout=60_000):
        """Poll the group's cached-members REST count until it equals *expected*.

        The refresh job runs in a worker, and the detail view does not update itself when
        it finishes, so there is nothing on the page to wait on. Instead, the browser
        fetches the members endpoint (with its logged-in session) once a second, and the
        wait fails with a TimeoutError if the count has not reached *expected* within
        *timeout* milliseconds. Reload the page afterwards to assert the count in the UI.
        """
        self.page.wait_for_function(
            """async ([url, expected]) => {
                const response = await fetch(url, {headers: {Accept: "application/json"}});
                return response.ok && (await response.json()).count === expected;
            }""",
            arg=[self.MEMBERS_API_PATH.format(pk=pk), expected],
            polling=1_000,
            timeout=timeout,
        )
