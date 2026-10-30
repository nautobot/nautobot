"""Page object for the Dynamic Group add and edit forms (/extras/dynamic-groups/add/ and <pk>/edit/)."""

import re

from playwright.sync_api import expect

from nautobot.playwright.base_page import select2_filter_pick
from nautobot.playwright.object_form_page import ObjectFormPage


class DynamicGroupFormPage(ObjectFormPage):
    """The Dynamic Group add form and the edit form's filter fields. The edit form opens from `click_edit`."""

    ADD_PATH = "/extras/dynamic-groups/add/"

    # The content type field is a plain <select>, so `select_option()` can pick an option by its value
    # (e.g. "dcim.device").
    _CONTENT_TYPE_SELECT = "select[name='content_type']"
    _PK_IN_URL = re.compile(r"/extras/dynamic-groups/([0-9a-f-]{36})/")

    def create(self, name, content_type):
        """Fill and submit the add form, returning the new group's pk from the detail-view redirect."""
        self.fill_input("name", name)
        self.page.locator(self._CONTENT_TYPE_SELECT).select_option(value=content_type)
        self.submit()
        match = self._PK_IN_URL.search(self.current_url())
        assert match, f"Creating the group did not redirect to its detail view (now on {self.current_url()})."
        return match.group(1)

    def add_filter_value(self, field_name, value):
        """Add *value* to the edit form's multi-value filter field *field_name* (e.g. "location").

        The option text is matched as a substring, because location options show their full ancestry path.
        """
        select2_filter_pick(self.page, f"filter-{field_name}", search=value, pick_text=value, exact=False)
        expect(self.page.locator(f"select[name='filter-{field_name}'] option:checked", has_text=value)).to_have_count(1)

    def save(self):
        """Submit the edit form and assert that it redirected away from the form."""
        self.submit()
        self.expect_url_lacks("/edit/")
