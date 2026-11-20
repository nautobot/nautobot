"""Page object for the Custom Fields list view (/extras/custom-fields/)."""

from nautobot.playwright.list_page import ListPage


class CustomFieldsPage(ListPage):
    """The Custom Fields list view. ListPage provides click_add for the Add button."""

    LIST_PATH = "/extras/custom-fields/"
