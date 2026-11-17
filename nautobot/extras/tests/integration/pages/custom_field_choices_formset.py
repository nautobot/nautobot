"""Component for the Custom Field Choices rows on the custom field add and edit forms."""

from playwright.sync_api import expect


class CustomFieldChoicesFormset:
    """The Custom Field Choices card: one row per choice, plus the rows that jquery.formset.js adds and deletes.

    Each row is identified by its form index, the number in its input names
    (`custom_field_choices-<index>-value`). The add form starts with 5 blank rows. The edit form
    starts with one row per saved choice, followed by 5 blank rows.
    """

    _CARD = "#nb-custom-field-choices-card"
    _PREFIX = "custom_field_choices"
    _ROWS = f"#custom-field-choices tr.formset_row-{_PREFIX}"
    # jquery.formset.js puts the add link in its own row after the last choice row, and a delete link in the
    # last cell of each choice row.
    _ADD_ROW = "#custom-field-choices a.add-row"
    _DELETE_ROW = "a.delete-row"
    _FIELD = "[name='" + _PREFIX + "-{index}-{name}']"
    # The form template lists each field's errors as list items in the field's cell.
    _ROW_ERRORS = "li.text-danger"

    def __init__(self, page):
        """Bind the component to a Playwright *page* that shows the custom field form."""
        self.page = page

    def _field(self, index, name):
        """Locator for the input *name* ("value" or "weight") of the row at *index*."""
        return self.page.locator(self._FIELD.format(index=index, name=name))

    def _row(self, index):
        """Locator for the row at *index*."""
        return self.page.locator(self._ROWS).filter(has=self._field(index, "value"))

    def _visible_rows(self):
        """Locator for the rows that are shown. A deleted saved choice stays in the DOM, hidden."""
        return self.page.locator(f"{self._ROWS}:visible")

    # -------------------------------------------------------------------------
    # Changing the rows
    # -------------------------------------------------------------------------

    def fill(self, index, value, weight=None):
        """Type *value*, and *weight* if given, into the row at *index*."""
        self._field(index, "value").fill(value)
        if weight is not None:
            self._field(index, "weight").fill(str(weight))

    def add_row(self):
        """Click "Add another Custom Field Choice", wait for the new row, and return its index.

        Indexes count every row in the DOM, including hidden ones, so the new row's index is the
        number of rows before the click.
        """
        index = self.page.locator(self._ROWS).count()
        self.page.locator(self._ADD_ROW).click()
        expect(self._field(index, "value")).to_be_visible()
        return index

    def delete_row(self, index):
        """Click the delete link of the row at *index* and wait until the row is no longer shown.

        A row for a saved choice is hidden and marked for deletion. A new row is removed.
        """
        row = self._row(index)
        row.locator(self._DELETE_ROW).click()
        expect(row).to_be_hidden()

    # -------------------------------------------------------------------------
    # Assertions
    # -------------------------------------------------------------------------

    def expect_visible(self):
        """Assert (auto-retrying) that the Custom Field Choices card is shown."""
        expect(self.page.locator(self._CARD)).to_be_visible()

    def expect_hidden(self):
        """Assert (auto-retrying) that the Custom Field Choices card is hidden."""
        expect(self.page.locator(self._CARD)).to_be_hidden()

    def expect_row_count(self, count):
        """Assert (auto-retrying) that *count* rows are shown."""
        expect(self._visible_rows()).to_have_count(count)

    def expect_row(self, index, value, weight=None):
        """Assert (auto-retrying) that the row at *index* holds *value*, and *weight* if given."""
        expect(self._field(index, "value")).to_have_value(value)
        if weight is not None:
            expect(self._field(index, "weight")).to_have_value(str(weight))

    def expect_row_error(self, index, text):
        """Assert (auto-retrying) that the row at *index* shows the error *text*."""
        expect(self._row(index).locator(self._ROW_ERRORS)).to_contain_text(text)
