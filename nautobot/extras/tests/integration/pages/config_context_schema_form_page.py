"""Page object for the Config Context Schema add form (/extras/config-context-schemas/add/)."""

import json
import re

from playwright.sync_api import expect

from nautobot.playwright.base_page import BasePage


class ConfigContextSchemaFormPage(BasePage):
    """The add form. Fill and submit it, then check the redirect or the error on the data_schema field."""

    ADD_PATH = "/extras/config-context-schemas/add/"

    _HEADING = "#page-title"
    _NAME = "input[name='name']"
    _DESCRIPTION = "input[name='description']"
    _DATA_SCHEMA = "textarea[name='data_schema']"
    _CREATE_BUTTON = "button[name='_create']"
    _DATA_SCHEMA_CONTAINER = "#id_data_schema-container"
    _DATA_SCHEMA_ERROR = "#id_data_schema_error"

    def navigate(self):
        """Go to the add form."""
        self._goto(self.ADD_PATH)

    def expect_heading(self, heading):
        """Assert (auto-retrying) that the page heading is *heading*."""
        expect(self.page.locator(self._HEADING)).to_have_text(heading)

    def fill(self, name, data_schema, description=""):
        """Fill the form. *data_schema* is the JSON text typed into the textarea."""
        self.page.fill(self._NAME, name)
        self.page.fill(self._DESCRIPTION, description)
        self.page.fill(self._DATA_SCHEMA, data_schema)

    def submit(self):
        """Click Create and wait for the next page to load.

        A valid submit redirects to the detail view, and a rejected submit renders the form again.
        """
        self._click_and_wait_for_navigation(self._CREATE_BUTTON)

    def expect_on_add_form(self):
        """Assert (auto-retrying) that the browser is still on the add form, so the submit did not redirect."""
        expect(self.page).to_have_url(re.compile(re.escape(self.ADD_PATH) + r"$"))

    def expect_data_schema_error(self, text, exact=False):
        """Assert (auto-retrying) that the data_schema field is flagged and its error shows *text*."""
        expect(self.page.locator(self._DATA_SCHEMA_CONTAINER)).to_have_class(re.compile(r"\bhas-error\b"))
        error = self.page.locator(self._DATA_SCHEMA_ERROR)
        if exact:
            expect(error).to_have_text(text)
        else:
            expect(error).to_contain_text(text)

    def expect_name(self, name):
        """Assert (auto-retrying) that the name input holds *name*."""
        expect(self.page.locator(self._NAME)).to_have_value(name)

    def get_data_schema(self):
        """Return the data_schema textarea's content parsed as JSON. Reads once, with no retry.
        A rejected form displays the schema again as JSON with sorted keys and indentation, so
        the textarea does not contain the text that was typed. Compare the parsed value instead.
        """
        return json.loads(self.page.locator(self._DATA_SCHEMA).input_value())
