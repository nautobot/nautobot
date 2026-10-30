"""Component for the embedded-action modal of an object create form.

A related-object field on a create form can have two buttons, "Add a new <model>" and
"Search <models>". Each loads a form into the one `#embedded_action_modal` the create form
renders. Creating an object there, or picking a search result, closes the modal and selects
that object in the field the button belongs to.

    form = DeviceCreatePage(auth_page, base_url)
    form.navigate()
    modal = EmbeddedModal(form)
    modal.open_create("tenant")
"""

import re
from urllib.parse import urlparse

from playwright.sync_api import expect

from nautobot.playwright.object_form_page import ObjectFormPage


class EmbeddedModal:
    """The embedded create and search modal of an `ObjectFormPage`."""

    _MODAL = "#embedded_action_modal"
    _TITLE = "h2.modal-title"
    # The buttons are icons. Their accessible name starts with the icon glyph, and "Add a new tenant" is a prefix of
    # "Add a new tenant group", so match the visually hidden label exactly.
    _ACTION_BUTTON = "#nb-create-form button:has(.visually-hidden:text-is('{label}'))"
    _CREATE_BUTTON = "button[name='_create']"
    _SEARCH_FORM = "#object_embedded_search_form"
    _SEARCH_BUTTON = "#object_embedded_search_form button[type='submit']"
    # The results load over HTMX on open and on each search. The table renders even with no results.
    _RESULTS_TABLE = ".nb-embedded-search-results table"
    _RESULT_ROWS = ".nb-embedded-search-results tbody tr[role='button']"
    _RESULTS_INFO = ".nb-embedded-search-results .nb-paginator-info"
    # The parent form's Select2 widget renders right after its hidden `<select>`.
    _PARENT_FIELD = "#nb-create-form select[name='{name}']"
    _PARENT_FIELD_DISPLAY = "#nb-create-form select[name='{name}'] + .select2-container"

    def __init__(self, form: ObjectFormPage):
        """Bind the modal to the open create *form* whose fields it fills."""
        self.form = form
        self.page = form.page
        self.root = self.page.locator(self._MODAL)

    # -------------------------------------------------------------------------
    # Opening and closing
    # -------------------------------------------------------------------------

    def open_create(self, verbose_name):
        """Click "Add a new *verbose_name*" on the parent form and wait for the create form to load."""
        self._open(f"Add a new {verbose_name}")

    def open_search(self, verbose_name_plural):
        """Click "Search *verbose_name_plural*" on the parent form and wait for the first results to load.

        Waiting for the results matters: a search submitted while the initial request is in flight can be overwritten
        by its response.
        """
        self._open(f"Search {verbose_name_plural}")
        expect(self.root.locator(self._RESULTS_TABLE)).to_be_attached()

    def _open(self, label):
        """Click the parent form button labelled *label* and wait for the modal titled *label*."""
        self.page.locator(self._ACTION_BUTTON.format(label=label)).click()
        self.expect_title(label)

    def expect_title(self, text):
        """Assert (auto-retrying) that the modal is open and titled *text*."""
        expect(self.root).to_be_visible()
        expect(self.root.locator(self._TITLE)).to_have_text(text)

    def expect_closed(self):
        """Assert (auto-retrying) that the modal has closed."""
        expect(self.root).to_be_hidden()

    # -------------------------------------------------------------------------
    # Fields inside the modal
    # -------------------------------------------------------------------------

    def field(self, name):
        """Locator for the input or select named *name* in the modal form."""
        return self.root.locator(f"input[name='{name}'], select[name='{name}']")

    def fill(self, name, value):
        """Type *value* into the modal input named *name*."""
        self.root.locator(f"input[name='{name}']").fill(value)

    def pick(self, name, text):
        """Pick the option showing *text* in the modal's API-backed Select2 field *name*.

        The parent form has fields with the same names, e.g. `tenant_group`, so the click is scoped to the modal.
        Only one Select2 dropdown is open at a time, so the dropdown itself needs no scoping.
        """
        self.root.locator(f"select[name='{name}'] + .select2-container").click()
        self.page.locator(".select2-container--open .select2-search__field").first.fill(text)
        self.page.locator(".select2-dropdown .select2-results__option").filter(has_text=text).first.click()

    def expect_prefilled(self, name, *labels):
        """Assert (auto-retrying) that the modal select *name* has exactly the options *labels* selected.

        Checks the option labels, e.g. "DCIM | device", because a create form's content type value is a
        database id that differs between instances.
        """
        expect(self.root.locator(f"select[name='{name}'] option:checked")).to_have_text(list(labels))

    def expect_not_prefilled(self, name):
        """Assert (auto-retrying) that the modal select *name* has no option selected."""
        expect(self.root.locator(f"select[name='{name}'] option:checked")).to_have_count(0)

    # -------------------------------------------------------------------------
    # Create
    # -------------------------------------------------------------------------

    def submit_create(self):
        """Click Create in the modal. The new object's form posts over HTMX, so the page does not navigate."""
        self.root.locator(self._CREATE_BUTTON).click()

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    def search(self, **filters):
        """Set the search form fields named by *filters*, click Search and wait for the new results.

        A select field is picked by its option text, any other field is typed into. If a row from the old results is
        picked before the new results arrive, HTMX replaces that row while its request is still running, and the pick
        is lost.
        """
        for name, value in filters.items():
            if self.root.locator(f"select[name='{name}']").count():
                self.pick(name, value)
            else:
                self.fill(name, value)
        list_path = self.root.locator(self._SEARCH_FORM).get_attribute("hx-get")
        with self.page.expect_response(lambda response: urlparse(response.url).path == list_path):
            self.root.locator(self._SEARCH_BUTTON).click()
        self.form.wait_for_load()

    def result_rows(self, text=None):
        """Locator for the search result rows, only those showing *text* if given."""
        rows = self.root.locator(self._RESULT_ROWS)
        return rows.filter(has_text=text) if text else rows

    def expect_result_total(self, count):
        """Assert (auto-retrying) that the results report *count* matches in all, across every page."""
        expect(self.root.locator(self._RESULTS_INFO)).to_have_text(re.compile(rf"\bof {count}\s*$"))

    def select_result(self, text):
        """Pick the one result row showing *text*.

        The row's first cell links to the object, so a mouse click could follow the link. The row is a keyboard
        button, so focus it and press Enter.
        """
        row = self.result_rows(text)
        expect(row).to_have_count(1)
        row.focus()
        row.press("Enter")

    # -------------------------------------------------------------------------
    # The parent form
    # -------------------------------------------------------------------------

    def expect_parent_field(self, name, pk, display):
        """Assert (auto-retrying) that the parent form field *name* selects the object *pk* and shows *display*."""
        expect(self.page.locator(self._PARENT_FIELD.format(name=name))).to_have_value(pk)
        expect(self.page.locator(self._PARENT_FIELD_DISPLAY.format(name=name))).to_contain_text(display)
