"""Page object for the Platform detail view (/dcim/platforms/<pk>/)."""

from nautobot.playwright.detail_page import DetailPage


class PlatformDetailPage(DetailPage):
    """The Platform detail view."""

    DETAIL_PATH = "/dcim/platforms/{pk}/"
    VERBOSE_NAME = "Platform"
