"""Page object for the Dynamic Group detail view (/extras/dynamic-groups/<pk>/)."""

import time
from urllib.parse import urlencode

from playwright.sync_api import expect

from nautobot.playwright.detail_page import DetailPage


class DynamicGroupDetailPage(DetailPage):
    """The Dynamic Group detail view: the Members count and the Refresh Members button."""

    DETAIL_PATH = "/extras/dynamic-groups/{pk}/"
    VERBOSE_NAME = "Dynamic Group"
    # The Members tab is a view of its own, not a pane of the detail view.
    MEMBERS_PATH = "/extras/dynamic-groups/{pk}/members/"
    # `wait_for_member_count` reads the group's cached members from this endpoint.
    MEMBERS_API_PATH = "/api/extras/dynamic-groups/{pk}/members/?limit=1"

    # The Members tab label contains a count badge, which is rendered only when the count is not zero.
    _MEMBERS_TAB_BADGE = "a[role='tab'][aria-controls='members'] span.badge"
    # "Refresh Members" is a JobButton that asks for confirmation. Its `data-bs-target` contains the id of
    # the modal (the id includes the JobButton pk), and the modal's submit button runs the job.
    _REFRESH_MEMBERS_BUTTON = "button[data-bs-toggle='modal']:has-text('Refresh Members')"
    _MODAL_CONFIRM_BUTTON = "button[type='submit']"
    _MEMBERS_TABLE_BODY = "table tbody"

    def navigate_members(self, pk, **params):
        """Go to the Members tab of the group *pk*, optionally with query *params* such as `per_page`."""
        path = self.MEMBERS_PATH.format(pk=pk)
        self._goto(f"{path}?{urlencode(params)}" if params else path)

    def expect_member_listed(self, name, listed=True):
        """Assert (auto-retrying) that the Members tab's table links to the member *name*, or that it does not."""
        link = self.page.locator(self._MEMBERS_TABLE_BODY).get_by_role("link", name=name, exact=True)
        expect(link).to_have_count(1 if listed else 0)

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
