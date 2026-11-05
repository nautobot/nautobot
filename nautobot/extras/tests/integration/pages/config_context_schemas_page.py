"""Page object for the Config Context Schemas list view (/extras/config-context-schemas/)."""

from nautobot.playwright.list_page import ListPage


class ConfigContextSchemasPage(ListPage):
    """The Config Context Schemas list view. Adds the Add button to ListPage."""

    LIST_PATH = "/extras/config-context-schemas/"

    _ADD_BUTTON = "#add-button"

    def click_add(self):
        """Click Add and wait for the add form to load."""
        self._click_and_wait_for_navigation(self._ADD_BUTTON)
