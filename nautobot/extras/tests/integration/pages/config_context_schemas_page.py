"""Page object for the Config Context Schemas list view (/extras/config-context-schemas/)."""

from nautobot.playwright.list_page import ListPage


class ConfigContextSchemasPage(ListPage):
    """The Config Context Schemas list view. The click on the Add button comes from ListPage."""

    LIST_PATH = "/extras/config-context-schemas/"
