"""Page object for the global search results page (/search/?q=...)."""

from urllib.parse import urlencode

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


class SearchResultsPage(BasePage):
    """The global search results page.

    The page loads as empty placeholders and each model's results arrive in their own HTMX request,
    so wait for the model whose results the test needs before reading or scanning the page.
    """

    PATH = "/search/"

    # `search.html` gives each model's results `id="<model slug>-results-table"`, where the slug is
    # Django's `slugify` of the content type, so "dcim.location" becomes "dcimlocation".
    _RESULTS_TABLE = "#{slug}-results-table table"

    def navigate(self, query):
        """Go to the search results for *query*."""
        self._goto(f"{self.PATH}?{urlencode({'q': query})}")

    def expect_results_for(self, content_type):
        """Assert (auto-retrying) that the results table for *content_type* (such as "dcim.location") has arrived."""
        slug = content_type.replace(".", "")
        expect(self.page.locator(self._RESULTS_TABLE.format(slug=slug))).to_be_attached()
