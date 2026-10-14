"""Page object for the Webhook add and edit forms and their conditions editor."""

import json
import re

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage, select2_filter_pick


class WebhookFormPage(BasePage):
    """The Webhook add and edit forms.

    A condition row is addressed by its index, which prefixes every control in it as `condition-<index>-`.
    """

    ADD_PATH = "/extras/webhooks/add/"
    EDIT_PATH = "/extras/webhooks/{pk}/edit/"

    _NAME_FIELD = "#id_name"
    _ENABLED_CHECKBOX = "#id_enabled"
    _TYPE_UPDATE_CHECKBOX = "#id_type_update"
    _PAYLOAD_URL_FIELD = "#id_payload_url"
    _CONDITIONS_FIELD = "#id_conditions"
    _CONDITION_ROW = "#conditions-rows .nb-condition"
    _ADD_CONDITION_BUTTON = "#conditions-add"
    _REMOVE_CONDITION_BUTTON_NAME = "Remove this condition"
    _CONDITIONS_COUNT = "#conditions-count"
    # `conditions-editor.js` sets `data-nb-drawing` on this form while the rows are drawn from the JSON field.
    _CONDITIONS_FORM = "form:has(#id_conditions)"
    _CREATE_BUTTON = "button[name='_create']"
    _DETAIL_URL = re.compile(r"/extras/webhooks/(?P<pk>[0-9a-f-]{36})/$")

    def navigate(self):
        """Go to the add form and wait for the conditions editor to draw its rows."""
        self._goto(self.ADD_PATH)
        self._wait_until_rows_are_drawn()

    def navigate_to_edit(self, pk):
        """Go to the edit form of the webhook *pk* and wait for the conditions editor to draw its rows."""
        self._goto(self.EDIT_PATH.format(pk=pk))
        self._wait_until_rows_are_drawn()

    def _wait_until_rows_are_drawn(self):
        expect(self.page.locator(self._CONDITIONS_FORM)).to_have_attribute("data-nb-drawing", "false")

    def fill_name_and_payload_url(self, name, payload_url):
        """Fill in the name and the payload URL, and call the webhook on update, with the webhook disabled so it never sends.

        A webhook needs at least one event.
        """
        self.page.locator(self._NAME_FIELD).fill(name)
        self.page.locator(self._ENABLED_CHECKBOX).uncheck()
        self.page.locator(self._TYPE_UPDATE_CHECKBOX).check()
        self.page.locator(self._PAYLOAD_URL_FIELD).fill(payload_url)

    def _condition_row(self, index):
        return self.page.locator(f"{self._CONDITION_ROW}[data-nb-condition-index='{index}']")

    def _pick_and_wait_for_new_row(self, index, name, text):
        """Pick *text* in a control that asks for its row again, and wait until the new row has replaced the old one."""
        old_row = self._condition_row(index).element_handle()
        select2_filter_pick(self.page, f"condition-{index}-{name}", search=text, pick_text=text)
        self.page.wait_for_function("row => !row.isConnected", arg=old_row)

    def pick_content_type(self, text):
        """Add the object type reading *text* and wait until every row has been drawn again."""
        select2_filter_pick(self.page, "content_types", search=text, pick_text=text)
        self._wait_until_rows_are_drawn()

    def pick_condition_type(self, index, text):
        """Choose the condition type reading *text* in the row at *index*."""
        self._pick_and_wait_for_new_row(index, "type", text)

    def pick_condition_field(self, index, text):
        """Choose the field reading *text* in the row at *index*."""
        self._pick_and_wait_for_new_row(index, "field", text)

    def pick_condition_value(self, index, key, text):
        """Choose *text* in the value control *key* of the row at *index*."""
        select2_filter_pick(self.page, f"condition-{index}-{key}", search=text, pick_text=text)

    def add_condition(self):
        """Click Add another Condition and wait for the new row to arrive."""
        rows = self.page.locator(self._CONDITION_ROW)
        expected = rows.count() + 1
        self.page.locator(self._ADD_CONDITION_BUTTON).click()
        expect(rows).to_have_count(expected)

    def remove_condition(self, index):
        """Click the remove button of the row at *index*."""
        self._condition_row(index).get_by_role("button", name=self._REMOVE_CONDITION_BUTTON_NAME).click()

    def expect_announced_count(self, text):
        """Assert (auto-retrying) that the live region tells a screen reader *text*, such as "2 conditions"."""
        expect(self.page.locator(self._CONDITIONS_COUNT)).to_have_text(text)

    def save(self) -> str:
        """Submit the add form and return the ID of the saved webhook, read from the detail view it redirects to."""
        self._click_and_wait_for_navigation(self._CREATE_BUTTON)
        saved = self._DETAIL_URL.search(self.page.url)
        if saved is None:
            raise AssertionError(f"Create did not redirect to a webhook. Page is at {self.page.url}")
        return saved.group("pk")

    def get_conditions(self):
        """The conditions the form would submit, read from the JSON field once, with no retry."""
        return json.loads(self.page.locator(self._CONDITIONS_FIELD).input_value())

    def get_condition_row_selections(self, index):
        """What each select of the row at *index* has chosen, keyed by the control name without its row prefix.

        Reads once, with no retry.
        """
        prefix = f"condition-{index}-"
        selects = self._condition_row(index).locator("select").all()
        return {select.get_attribute("name").removeprefix(prefix): select.input_value() for select in selects}

    def get_condition_row_indexes(self):
        """The index of every row, in the order the rows are shown. Reads once, with no retry."""
        rows = self.page.locator(self._CONDITION_ROW).all()
        return [int(row.get_attribute("data-nb-condition-index")) for row in rows]
