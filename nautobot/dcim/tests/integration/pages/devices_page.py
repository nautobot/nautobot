"""Page object for the Devices list view (/dcim/devices/)."""

from nautobot.playwright.list_page import ListPage


class DevicesPage(ListPage):
    """The Devices list view. List and table-configuration behavior comes from ListPage."""

    LIST_PATH = "/dcim/devices/"
