"""Page object for the Location detail view (/dcim/locations/<pk>/)."""

from nautobot.playwright.detail_page import DetailPage


class LocationDetailPage(DetailPage):
    """The Location detail view."""

    DETAIL_PATH = "/dcim/locations/{pk}/"
    VERBOSE_NAME = "Location"
