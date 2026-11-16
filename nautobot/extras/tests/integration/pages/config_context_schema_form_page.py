"""Page object for the Config Context Schema add form (/extras/config-context-schemas/add/)."""

import json

from nautobot.playwright.object_form_page import ObjectFormPage


class ConfigContextSchemaFormPage(ObjectFormPage):
    """The add form. Adds to ObjectFormPage a method that fills the form and one that reads the data_schema textarea."""

    ADD_PATH = "/extras/config-context-schemas/add/"

    _DATA_SCHEMA = "textarea[name='data_schema']"

    def fill(self, name, data_schema, description=""):
        """Fill the form. *data_schema* is the JSON text typed into the textarea."""
        self.fill_input("name", name)
        self.fill_input("description", description)
        self.fill_input("data_schema", data_schema)

    def get_data_schema(self):
        """Return the data_schema textarea's content parsed as JSON. Reads once, with no retry.

        A rejected form displays the schema again as JSON with sorted keys and indentation, so
        the textarea does not contain the text that was typed. Compare the parsed value instead.
        """
        return json.loads(self.page.locator(self._DATA_SCHEMA).input_value())
