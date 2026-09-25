"""Page object for the Radio Profiles list view (/wireless/radio-profiles/)."""

from nautobot.playwright.edit_page import EditPage


class RadioProfilesPage(EditPage):
    """The Radio Profiles list view. Row selection comes from ListPage, the bulk edit form from EditPage."""

    LIST_PATH = "/wireless/radio-profiles/"
