"""Shared page object for object add and edit forms.

Subclasses set ADD_PATH:

    class DeviceCreatePage(ObjectFormPage):
        ADD_PATH = "/dcim/devices/add/"
"""

import re

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


class ObjectFormPage(BasePage):
    """Open, fill and submit an object add or edit form."""

    ADD_PATH = ""  # REQUIRED in subclass, e.g. "/dcim/devices/add/"

    _HEADING = "#page-title"
    # A text field renders as an input or, for longer text such as JSON, a textarea.
    _TEXT_FIELD = "input[name='{field_name}'], textarea[name='{field_name}']"
    # The add form has a Create button and the edit form has an Update button.
    _SUBMIT_BUTTON = "button[name='_create'], button[name='_update']"
    # render_field.html wraps each field in a container that gets the has-error class when the field is invalid,
    # and lists the field's errors in an element whose id contains the field name.
    _FIELD_CONTAINER = "#id_{field_name}-container"
    _FIELD_ERRORS = "#id_{field_name}_error"
    # Every detail URL ends in the object's pk. The group is unnamed because `to_have_url()` passes
    # the pattern to the browser as a JavaScript RegExp, which does not accept `(?P<name>...)`.
    _PK_IN_DETAIL_URL = re.compile(r"/([0-9a-f-]{36})/$")

    def __init__(self, page, base_url):
        """Fail fast on a subclass that forgot to set `ADD_PATH`."""
        if not self.ADD_PATH:
            raise ValueError(f"{type(self).__name__} must set ADD_PATH (e.g. '/dcim/devices/add/').")
        super().__init__(page, base_url)

    def navigate(self):
        """Go to the empty add form and wait for its submit button."""
        self._goto(self.ADD_PATH)
        expect(self.page.locator(self._SUBMIT_BUTTON)).to_be_attached()

    def expect_heading(self, text):
        """Assert (auto-retrying) that the page heading is *text*."""
        expect(self.page.locator(self._HEADING)).to_have_text(text)

    def fill_input(self, field_name, value):
        """Type *value* into the text input or textarea named *field_name*."""
        self.page.locator(self._TEXT_FIELD.format(field_name=field_name)).fill(value)

    def pick_related(self, field_name, record, search=None):
        """Pick the API *record* in the Select2 field *field_name* by its `display` text.

        Pass *search* when the API search does not match the `display` text.
        """
        self.select2_filter_pick(field_name, search=search or record["display"], pick_text=record["display"])

    def submit(self):
        """Click Create or Update and wait for the next page to load.

        This does not check whether the server accepted the form. The next page is the new or
        updated object on success, or the same form redisplayed with errors on failure, and
        tests rely on both (e.g. test_accessibility.py submits an invalid form and then calls
        `expect_validation_errors`). Subclasses that expect success should check the outcome
        themselves.
        """
        self._click_and_wait_for_navigation(self._SUBMIT_BUTTON)

    def submit_and_return_pk(self):
        """Click Create, wait for the redirect to the new object's detail view, and return its pk."""
        self.submit()
        expect(self.page).to_have_url(self._PK_IN_DETAIL_URL)
        return self._PK_IN_DETAIL_URL.search(self.page.url).group(1)

    def expect_on_add_form(self):
        """Assert (auto-retrying) that the browser is still on the add form, so the submit did not redirect."""
        expect(self.page).to_have_url(re.compile(re.escape(self.ADD_PATH) + r"$"))

    def expect_input_value(self, field_name, value):
        """Assert (auto-retrying) that the text input or textarea named *field_name* has the value *value*."""
        expect(self.page.locator(self._TEXT_FIELD.format(field_name=field_name))).to_have_value(value)

    def expect_field_error(self, field_name, text, exact=False):
        """Assert (auto-retrying) that field *field_name* is marked invalid and its error list shows *text*.

        The field is marked invalid when its container has the has-error class.
        """
        container = self.page.locator(self._FIELD_CONTAINER.format(field_name=field_name))
        expect(container).to_have_class(re.compile(r"\bhas-error\b"))
        errors = self.page.locator(self._FIELD_ERRORS.format(field_name=field_name))
        if exact:
            expect(errors).to_have_text(text)
        else:
            expect(errors).to_contain_text(text)
