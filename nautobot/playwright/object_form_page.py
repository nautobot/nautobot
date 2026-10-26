"""Shared page object for object add and edit forms.

Subclasses set ADD_PATH:

    class DeviceCreatePage(ObjectFormPage):
        ADD_PATH = "/dcim/devices/add/"
"""

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage, select2_filter_pick


class ObjectFormPage(BasePage):
    """Open, fill and submit an object add or edit form."""

    ADD_PATH = ""  # REQUIRED in subclass, e.g. "/dcim/devices/add/"

    # Create on the add form, Update on the edit form.
    _SUBMIT_BUTTON = "button[name='_create'], button[name='_update']"

    def __init__(self, page, base_url):
        """Fail fast on a subclass that forgot to set `ADD_PATH`."""
        if not self.ADD_PATH:
            raise ValueError(f"{type(self).__name__} must set ADD_PATH (e.g. '/dcim/devices/add/').")
        super().__init__(page, base_url)

    def navigate(self):
        """Go to the empty add form and wait for its submit button."""
        self._goto(self.ADD_PATH)
        expect(self.page.locator(self._SUBMIT_BUTTON)).to_be_attached()

    def fill_input(self, field_name, value):
        """Type *value* into the text input named *field_name*."""
        self.page.locator(f"input[name='{field_name}']").fill(value)

    def pick_related(self, field_name, record, search=None):
        """Pick the API *record* in the Select2 field *field_name* by its `display` text.

        Pass *search* when the API search does not match the `display` text.
        """
        select2_filter_pick(self.page, field_name, search=search or record["display"], pick_text=record["display"])

    def submit(self):
        """Click Create or Update and wait for the next page to load."""
        self._click_and_wait_for_navigation(self._SUBMIT_BUTTON)
