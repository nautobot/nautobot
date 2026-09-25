"""Shared page object for list views with a bulk edit form.

Every model's bulk edit form (`<list>/edit/`) renders the same heading, hidden pk
inputs, and Apply button, and submitting it enqueues the same "Bulk Edit Objects" job,
so that behavior lives here. Subclasses set `LIST_PATH` as for `ListPage`:

    class RadioProfilesPage(EditPage):
        LIST_PATH = "/wireless/radio-profiles/"
"""

import re

from playwright.sync_api import expect

from nautobot.playwright.base_page import select2_filter_pick
from nautobot.playwright.list_page import ListPage


class EditPage(ListPage):
    """List-view behavior from ListPage plus the bulk edit form it opens."""

    # The bulk edit form carries the selected ids as hidden pk inputs.
    _BULK_EDIT_PKS = "form input[type='hidden'][name='pk']"
    _BULK_EDIT_APPLY = "button[name='_apply']"
    _JOB_RESULT_URL = re.compile(r"/extras/job-results/(?P<pk>[0-9a-f-]{36})/")

    def expect_bulk_edit_count(self, count):
        """Assert (auto-retrying) that the bulk edit form's heading states it edits *count* objects."""
        expect(self.page.locator("h1", has_text=re.compile(rf"\bEditing {count} "))).to_have_count(1)

    def get_bulk_edit_pks(self) -> list:
        """Ids of the objects the bulk edit form will submit, read from its hidden pk inputs."""
        return [pk.get_attribute("value") for pk in self.page.locator(self._BULK_EDIT_PKS).all()]

    def set_bulk_edit_field(self, field_name, label):
        """Choose an option in a bulk edit dropdown by the text, e.g. "5 GHz" for frequency."""
        select2_filter_pick(self.page, field_name, search=label, pick_text=label)

    def apply_bulk_edit(self) -> str:
        """Submit the form and return the job result id from the redirect URL."""
        self.page.locator(self._BULK_EDIT_APPLY).click()
        self.page.wait_for_url(self._JOB_RESULT_URL, wait_until="commit")
        return self._JOB_RESULT_URL.search(self.page.url).group("pk")
