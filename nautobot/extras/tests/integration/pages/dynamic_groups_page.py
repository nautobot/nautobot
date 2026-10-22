"""Page object for the Dynamic Group add, edit, and detail views (/extras/dynamic-groups/)."""

import re
import time

from playwright.sync_api import expect

from nautobot.playwright.base_page import select2_filter_pick
from nautobot.playwright.detail_page import DetailPage


class DynamicGroupPage(DetailPage):
    """The dynamic group detail view, add form, and edit-form filter fields."""

    DETAIL_PATH = "/extras/dynamic-groups/{pk}/"
    VERBOSE_NAME = "Dynamic Group"
    ADD_PATH = "/extras/dynamic-groups/add/"
    EDIT_PATH = "/extras/dynamic-groups/{pk}/edit/"
    # `wait_for_member_count` reads the group's cached members from this endpoint.
    MEMBERS_API_PATH = "/api/extras/dynamic-groups/{pk}/members/?limit=1"

    _NAME_INPUT = "input[name='name']"
    # The content type field is a plain <select>, so `select_option()` can pick an option by its value
    # (e.g. "dcim.device").
    _CONTENT_TYPE_SELECT = "select[name='content_type']"
    _CREATE_BUTTON = "button[name='_create']"
    _UPDATE_BUTTON = "button[name='_update']"
    # The Members tab label contains a count badge, which is rendered only when the count is not zero.
    _MEMBERS_TAB_BADGE = "a[role='tab'][aria-controls='members'] span.badge"
    # "Refresh Members" is a JobButton that asks for confirmation. Its `data-bs-target` contains the id of
    # the modal (the id includes the JobButton pk), and the modal's submit button runs the job.
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
        """Go to the edit form of the group *pk*."""
        self._goto(self.EDIT_PATH.format(pk=pk))

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

        The option text is matched as a substring, because location options show their full ancestry path.
        """
        select2_filter_pick(self.page, f"filter-{field_name}", search=value, pick_text=value, exact=False)
        expect(self.page.locator(f"select[name='filter-{field_name}'] option:checked", has_text=value)).to_have_count(1)

    def save(self):
        """Submit the edit form and assert that it redirected away from the form."""
        self._click_and_wait_for_navigation(self._UPDATE_BUTTON)
        self.expect_url_lacks("/edit/")

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

        This only enqueues the refresh job. Call `wait_for_member_count` before asserting
        on the new membership.
        """
        button = self.page.locator(self._REFRESH_MEMBERS_BUTTON).first
        modal = button.get_attribute("data-bs-target")
        assert modal, "The Refresh Members button names no confirmation modal."
        button.click()
        confirm = f"{modal} {self._MODAL_CONFIRM_BUTTON}"
        self.page.locator(confirm).wait_for(state="visible")
        self._click_and_wait_for_navigation(confirm)

    def wait_for_member_count(self, pk, expected, timeout=60, interval=1):
        """Poll the group's cached-members REST count until it equals *expected*.

        The detail view does not update itself when the refresh job finishes, so the wait reads
        the members endpoint every *interval* seconds through `page.request`, which uses the
        browser's logged-in session. It fails if the count has not reached *expected* within
        *timeout* seconds. Reload the page afterwards to assert the count in the UI.
        """
        url = self.MEMBERS_API_PATH.format(pk=pk)
        deadline = time.monotonic() + timeout
        while True:
            response = self.page.request.get(url, headers={"Accept": "application/json"})
            assert response.ok, f"GET {url} returned {response.status}: {response.text()[:200]}"
            count = response.json()["count"]
            if count == expected:
                return
            if time.monotonic() >= deadline:
                raise AssertionError(
                    f"Group {pk} still has {count} cached members after {timeout}s, expected {expected}. "
                    "Is a Celery worker consuming the Refresh Members job's queue?"
                )
            self.page.wait_for_timeout(interval * 1_000)
