"""Shared page object for the Job Result detail view (/extras/job-results/<pk>/).

Bulk edit and bulk delete in every app redirect here, so it is shared rather than
kept with the extras tests.
"""

from playwright.sync_api import expect

from nautobot.playwright.detail_page import DetailPage


class JobResultPage(DetailPage):
    """The Job Result detail view."""

    DETAIL_PATH = "/extras/job-results/{pk}/"
    VERBOSE_NAME = "Job Result"

    _SUMMARY_PANEL = "Summary of Results"
    # The status badge keeps this id through every refresh of the summary panel.
    _STATUS = "#pending-result-label"

    def expect_job_description(self, description):
        """Assert (auto-retrying) that the summary panel gives the job's description as *description*."""
        self.expect_panel_field(self._SUMMARY_PANEL, "Job Description", description)

    def expect_status(self, status, timeout=60_000):
        """Assert that the job reaches *status* (e.g. "Completed") within *timeout* ms.

        The summary panel polls every 3 seconds while the job is unfinished, so the
        badge updates in place without a reload.
        """
        expect(self.page.locator(self._STATUS)).to_have_text(status, timeout=timeout)
