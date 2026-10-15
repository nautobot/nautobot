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
    _TYPE_SELECT2 = "select[data-nb-condition-role='type'] + span.select2-container"
    _REMOVE_CONDITION_BUTTON_NAME = "Remove this condition"
    _CONDITIONS_COUNT = "#conditions-count"
    _SELECT2_CONTAINER = "select[name='{name}'] + span.select2-container"
    # Select2 puts the text it shows in `title`. The element's own text also holds the × of its clear button.
    _SELECT2_SHOWN_TEXT = f"{_SELECT2_CONTAINER} .select2-selection__rendered"
    _SELECT2_PLACEHOLDER = ".select2-selection__placeholder"
    _SELECT2_DISABLED = re.compile(r"\bselect2-container--disabled\b")
    _FORM_TAB = "#conditions_form-tab"
    _JSON_TAB = "#conditions_json-tab"
    # What the server sends in place of the rows when the JSON field cannot be read as conditions.
    _UNREADABLE_MESSAGE = "#conditions-rows .nb-conditions-unreadable"
    # `conditions-editor.js` sets `data-nb-drawing` on this form while the rows are drawn from the JSON field.
    _CONDITIONS_FORM = "form:has(#id_conditions)"
    _CREATE_BUTTON = "button[name='_create']"
    _DETAIL_URL = re.compile(r"/extras/webhooks/(?P<pk>[0-9a-f-]{36})/$")
    # `{% render_field %}` gives a control's error list this id, which the control's `aria-describedby` names.
    _CONDITION_ERRORS = "#id_condition-{index}-{name}_error"
    # A day of the month the open flatpickr calendar shows, leaving out the days it shows from either side of it.
    _CALENDAR_DAY = ".flatpickr-calendar.open .flatpickr-day:not(.prevMonthDay):not(.nextMonthDay)"

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

    def fill_disabled_update_webhook(self, name, payload_url):
        """Fill in *name* and *payload_url* for a webhook called on update, disabled so it never sends."""
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

    def pick_condition_subfield(self, index, text):
        """Choose the sub-field reading *text* in the row at *index*."""
        self._pick_and_wait_for_new_row(index, "field_subfield", text)

    def pick_condition_operator(self, index, text):
        """Choose the operator reading *text* in the row at *index*."""
        self._pick_and_wait_for_new_row(index, "operator", text)

    def pick_condition_day(self, index, key, day):
        """Open the calendar of the date control *key* in the row at *index* and click *day* of the month it shows."""
        self.page.locator(f"[name='condition-{index}-{key}']").click()
        self.page.locator(self._CALENDAR_DAY).filter(has_text=re.compile(rf"^{day}$")).click()

    def pick_condition_negation(self, index, text):
        """Choose `When` or `Not When`, reading *text*, in the row at *index*. The row is not asked for again."""
        select2_filter_pick(self.page, f"condition-{index}-negate", search=text, pick_text=text)

    def pick_condition_value(self, index, key, text):
        """Choose *text* in the value control *key* of the row at *index*."""
        select2_filter_pick(self.page, f"condition-{index}-{key}", search=text, pick_text=text)

    def add_condition(self):
        """Click Add another Condition and wait until the editor has set up the new row and written the JSON field."""
        rows = self.page.locator(self._CONDITION_ROW)
        expected = rows.count() + 1
        self.page.locator(self._ADD_CONDITION_BUTTON).click()
        expect(rows).to_have_count(expected)
        # Select2 on the new row means the JSON field is written. One `htmx.onLoad` in `conditions-editor.js` does both.
        expect(rows.last.locator(self._TYPE_SELECT2)).to_be_visible()

    def remove_condition(self, index):
        """Click the remove button of the row at *index*."""
        self._condition_row(index).get_by_role("button", name=self._REMOVE_CONDITION_BUTTON_NAME).click()

    def expect_announced_count(self, text):
        """Assert (auto-retrying) that the live region tells a screen reader *text*, such as "2 conditions"."""
        expect(self.page.locator(self._CONDITIONS_COUNT)).to_have_text(text)

    def show_json_tab(self):
        """Switch the conditions editor to its JSON tab."""
        self.page.locator(self._JSON_TAB).click()

    def show_form_tab(self):
        """Switch the conditions editor to its Form tab and wait until the rows are drawn from the JSON field.

        The panes have no `fade`, so Bootstrap shows the tab, and the redraw starts, within the click.
        """
        self.page.locator(self._FORM_TAB).click()
        self._wait_until_rows_are_drawn()

    def fill_conditions(self, conditions):
        """Type *conditions* into the JSON field as JSON. The field is visible on the JSON tab only."""
        self.fill_conditions_text(json.dumps(conditions))

    def fill_conditions_text(self, text):
        """Type *text* into the JSON field unchanged, such as JSON that does not parse. Visible on the JSON tab only."""
        self.page.locator(self._CONDITIONS_FIELD).fill(text)

    def expect_conditions_text(self, text):
        """Assert (auto-retrying) that the JSON field holds exactly *text*."""
        expect(self.page.locator(self._CONDITIONS_FIELD)).to_have_value(text)

    def expect_unreadable_message(self):
        """Assert (auto-retrying) that a message stands in for the rows, because the JSON field cannot be read."""
        expect(self.page.locator(self._UNREADABLE_MESSAGE)).to_be_visible()

    def save(self) -> str:
        """Submit the add form and return the ID of the saved webhook, read from the detail view it redirects to."""
        self._click_and_wait_for_navigation(self._CREATE_BUTTON)
        saved = self._DETAIL_URL.search(self.page.url)
        if saved is None:
            raise AssertionError(f"Create did not redirect to a webhook. Page is at {self.page.url}")
        return saved.group("pk")

    def save_expecting_refusal(self):
        """Submit the add form, check that it came back unsaved, and wait until the rows are drawn with their errors."""
        self._click_and_wait_for_navigation(self._CREATE_BUTTON)
        if self._DETAIL_URL.search(self.page.url):
            raise AssertionError(f"Create saved the webhook instead of refusing it. Page is at {self.page.url}")
        self._wait_until_rows_are_drawn()

    def expect_condition_error(self, index, name, text):
        """Assert (auto-retrying) that the control *name* in the row at *index* shows the error *text*."""
        expect(self.page.locator(self._CONDITION_ERRORS.format(index=index, name=name))).to_contain_text(text)

    def get_conditions(self):
        """The conditions the form would submit, read from the JSON field once, with no retry."""
        return json.loads(self.page.locator(self._CONDITIONS_FIELD).input_value())

    def expect_condition_row_to_show(self, index, texts):
        """Assert (auto-retrying) that each Select2 named in *texts* shows its text in the row at *index*.

        *texts* is keyed by the control name without its row prefix, such as `{"type": "Field transition"}`.
        """
        for name, text in texts.items():
            shown = self.page.locator(self._SELECT2_SHOWN_TEXT.format(name=f"condition-{index}-{name}"))
            expect(shown).to_have_attribute("title", text)

    def expect_condition_row_to_show_nothing_in(self, index, name):
        """Assert (auto-retrying) that the Select2 of the control *name* in the row at *index* shows only `—`."""
        shown = self.page.locator(self._SELECT2_SHOWN_TEXT.format(name=f"condition-{index}-{name}"))
        expect(shown.locator(self._SELECT2_PLACEHOLDER)).to_be_visible()

    def expect_condition_select_enabled(self, index, name, enabled):
        """Assert (auto-retrying) that the Select2 of the control *name* in the row at *index* is *enabled* or not."""
        container = self.page.locator(self._SELECT2_CONTAINER.format(name=f"condition-{index}-{name}"))
        if enabled:
            expect(container).not_to_have_class(self._SELECT2_DISABLED)
        else:
            expect(container).to_have_class(self._SELECT2_DISABLED)

    def get_condition_row_inputs(self, index):
        """The value of each input of the row at *index*, keyed by the input name without its row prefix.

        Reads once, with no retry.
        """
        prefix = f"condition-{index}-"
        inputs = self._condition_row(index).locator("input[name]").all()
        return {control.get_attribute("name").removeprefix(prefix): control.input_value() for control in inputs}

    def get_condition_row_indexes(self):
        """The index of every row, in the order the rows are shown. Reads once, with no retry."""
        rows = self.page.locator(self._CONDITION_ROW).all()
        return [int(row.get_attribute("data-nb-condition-index")) for row in rows]
