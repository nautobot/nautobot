"""Page object for the Webhook add form (/extras/webhooks/add/) and its conditions editor."""

import json

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage, select2_filter_pick


class WebhookFormPage(BasePage):
    """The Webhook add form."""

    ADD_PATH = "/extras/webhooks/add/"

    _CONDITIONS_FIELD = "#id_conditions"
    _CONDITION_ROW = "#conditions-rows .nb-condition"
    # `conditions-editor.js` sets `data-nb-drawing` on this form while every row is drawn again from the JSON field.
    _CONDITIONS_FORM = "form:has(#id_conditions)"

    def navigate(self):
        """Go to the add form and wait for the conditions editor to draw its first row."""
        self._goto(self.ADD_PATH)
        self.page.locator(self._CONDITION_ROW).first.wait_for()

    def _pick_and_wait_for_new_row(self, index, name, text):
        """Pick *text* in a control that asks for its row again, and wait until the new row has replaced the old one."""
        old_row = self.page.locator(f"{self._CONDITION_ROW}[data-nb-condition-index='{index}']").element_handle()
        select2_filter_pick(self.page, f"condition-{index}-{name}", search=text, pick_text=text)
        self.page.wait_for_function("row => !row.isConnected", arg=old_row)

    def pick_content_type(self, text):
        """Add the object type reading *text* and wait until every row has been drawn again."""
        select2_filter_pick(self.page, "content_types", search=text, pick_text=text)
        expect(self.page.locator(self._CONDITIONS_FORM)).to_have_attribute("data-nb-drawing", "false")

    def pick_condition_type(self, index, text):
        """Choose the condition type reading *text* in the row at *index*."""
        self._pick_and_wait_for_new_row(index, "type", text)

    def pick_condition_field(self, index, text):
        """Choose the field reading *text* in the row at *index*."""
        self._pick_and_wait_for_new_row(index, "field", text)

    def pick_condition_value(self, index, key, text):
        """Choose *text* in the value control *key* of the row at *index*."""
        select2_filter_pick(self.page, f"condition-{index}-{key}", search=text, pick_text=text)

    def get_conditions(self):
        """The conditions the form would submit, read from the JSON field once, with no retry."""
        return json.loads(self.page.locator(self._CONDITIONS_FIELD).input_value())
