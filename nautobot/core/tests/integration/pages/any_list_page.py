"""Page object for a list view reached by its path rather than by its model."""

from nautobot.playwright.list_page import ListPage


class AnyListPage(ListPage):
    """A list view opened by path, for a test that visits many list views in one run.

    `LIST_PATH` is a placeholder that satisfies `ListPage`; `navigate_to` takes the path instead.
    """

    LIST_PATH = "/"

    def navigate_to(self, path):
        """Go to *path* and return the final response, after any redirect, so the caller can check its status."""
        response = self.page.goto(f"{self.base_url}{path}")
        self.wait_for_load()
        return response
