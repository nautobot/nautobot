"""Page object for the Manufacturers list view (/dcim/manufacturers/)."""

from nautobot.playwright.list_page import ListPage


class ManufacturersPage(ListPage):
    """The Manufacturers list view."""

    LIST_PATH = "/dcim/manufacturers/"
