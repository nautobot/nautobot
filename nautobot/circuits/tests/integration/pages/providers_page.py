"""Page object for the Providers list view (/circuits/providers/)."""

from nautobot.playwright.list_page import ListPage


class ProvidersPage(ListPage):
    """The Providers list view. List and filter-drawer behavior comes from ListPage."""

    LIST_PATH = "/circuits/providers/"
