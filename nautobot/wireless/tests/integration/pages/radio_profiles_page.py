"""Page object for the Radio Profiles list view (/wireless/radio-profiles/)."""

from nautobot.playwright.list_page import ListPage


class RadioProfilesPage(ListPage):
    """The Radio Profiles list view. Row selection and the bulk edit form come from ListPage."""

    LIST_PATH = "/wireless/radio-profiles/"
