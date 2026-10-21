"""Page object for a list view reached by its path rather than by its model."""

from nautobot.playwright.list_page import ListPage


class AnyListPage(ListPage):
    """A list view opened by its path, for a test that visits many list views in one run."""

    LIST_PATH = ""  # Set per instance from *path*.

    def __init__(self, page, base_url, path):
        self.LIST_PATH = path
        super().__init__(page, base_url)

    def navigate_with_response(self):
        """Go to the list view and return the final response, after any redirect, so the caller can check its status."""
        response = self.page.goto(f"{self.base_url}{self.LIST_PATH}")
        self.wait_for_load()
        return response
