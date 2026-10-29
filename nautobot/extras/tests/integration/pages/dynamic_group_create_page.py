"""Page object for the Dynamic Group add form (/extras/dynamic-groups/add/)."""

import re

from nautobot.playwright.object_form_page import ObjectFormPage


class DynamicGroupCreatePage(ObjectFormPage):
    """The Dynamic Group add form."""

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
