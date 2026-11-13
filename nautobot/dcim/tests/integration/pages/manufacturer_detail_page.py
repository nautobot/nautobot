"""Page object for the Manufacturer detail view (/dcim/manufacturers/<pk>/)."""

from nautobot.playwright.detail_page import DetailPage


class ManufacturerDetailPage(DetailPage):
    """The Manufacturer detail view."""

    DETAIL_PATH = "/dcim/manufacturers/{pk}/"
    VERBOSE_NAME = "Manufacturer"
