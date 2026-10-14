"""Config context schemas: the add form's valid and rejected submits, and the schema's Validation tab."""

import json

import pytest

from nautobot.extras.tests.integration.pages.config_context_schema_detail_page import ConfigContextSchemaDetailPage
from nautobot.extras.tests.integration.pages.config_context_schema_form_page import ConfigContextSchemaFormPage
from nautobot.extras.tests.integration.pages.config_context_schemas_page import ConfigContextSchemasPage
from nautobot.playwright.helpers import unique_name

ADD_FORM_HEADING = "Add a new config context schema"

VALID_SCHEMA_TEXT = '{"type": "object", "properties": {"a": {"type": "string"}}}'
# Rejected by the jsonschema library: "not a valid type" is not a JSON Schema type.
BAD_TYPE_SCHEMA_TEXT = '{"type": "object", "properties": {"a": {"type": "not a valid type"}}}'
# Rejected by ConfigContextSchema.clean(): context data is an object, so the schema must be an object with properties.
NON_OBJECT_SCHEMA_TEXT = '{"type": "array"}'
NON_OBJECT_ERROR = (
    "Nautobot only supports context data in the form of an object and thus the JSON schema "
    "must be of type object and specify a set of properties."
)

# Replacements for the schema created_schema_validation_tree starts from (a, b and c, all
# integers), each failing the {"a": 123, "b": 456, "c": 777} its children hold. The
# messages come from the jsonschema library.
RETYPED_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"a": {"type": "string"}, "b": {"type": "integer"}, "c": {"type": "integer"}},
}
RETYPED_ERROR = "123 is not of type 'string'"
RETYPED_COMPLIANT_DATA = {"a": "foo", "b": 456, "c": 777}
REQUIRED_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "a": {"type": "integer"},
        "b": {"type": "integer"},
        "c": {"type": "integer"},
        "d": {"type": "integer"},
    },
    "required": ["d"],
}
REQUIRED_ERROR = "'d' is a required property"


def schemas_named(api, name):
    """API records of every config context schema named *name*."""
    response = api.get("/api/extras/config-context-schemas/", params={"name": name})
    assert response.ok, f"GET config context schemas returned {response.status}: {response.text()}"
    return response.json()["results"]


def validation_rows(tree):
    """Map each Validation tab panel to the name of the one object created_schema_validation_tree owns in it."""
    return {
        "Config Contexts": tree["config_context"]["name"],
        "Devices": tree["device"]["name"],
        "Virtual Machines": tree["virtual_machine"]["name"],
    }


class ConfigContextSchemaTestCase:
    """Creating config context schemas through the add form, and the pass/fail states on the Validation tab."""

    # -------------------------------------------------------------------------
    # Replaces Selenium test_create_valid_config_context_schema
    # -------------------------------------------------------------------------

    @pytest.mark.behavioral
    def test_create_valid_config_context_schema(self, auth_page, base_url, api, schema_names_to_delete):
        """A valid schema submitted from the list's Add button is created and opens on its detail view."""
        name = unique_name()
        description = unique_name("ZZZ-description")
        schema_names_to_delete.append(name)

        schemas = ConfigContextSchemasPage(auth_page, base_url)
        schemas.navigate()
        schemas.click_add()

        form = ConfigContextSchemaFormPage(auth_page, base_url)
        form.expect_heading(ADD_FORM_HEADING)
        form.fill(name=name, data_schema=VALID_SCHEMA_TEXT, description=description)
        form.submit()

        detail = ConfigContextSchemaDetailPage(auth_page, base_url)
        detail.expect_success_message(f"Created config context schema {name}")
        detail.expect_heading(name)
        detail.expect_edit_button()

        records = schemas_named(api, name)
        assert len(records) == 1, f"Expected one schema named {name!r}, found {len(records)}"
        detail.expect_url_contains(detail.DETAIL_PATH.format(pk=records[0]["id"]))
        assert records[0]["data_schema"] == json.loads(VALID_SCHEMA_TEXT)
        assert records[0]["description"] == description

    # -------------------------------------------------------------------------
    # Replaces Selenium test_create_invalid_config_context_schema
    # -------------------------------------------------------------------------

    @pytest.mark.behavioral
    def test_create_invalid_config_context_schema_bad_jsonschema_type(
        self, auth_page, base_url, api, schema_names_to_delete
    ):
        """A schema the jsonschema library rejects redisplays the form with the error and the submitted input."""
        name = unique_name()
        # Deleted on teardown in case a jsonschema upgrade starts accepting the schema.
        schema_names_to_delete.append(name)

        form = ConfigContextSchemaFormPage(auth_page, base_url)
        form.navigate()
        form.fill(name=name, data_schema=BAD_TYPE_SCHEMA_TEXT)
        form.submit()

        form.expect_on_add_form()
        form.expect_heading(ADD_FORM_HEADING)
        # The wording belongs to jsonschema, so only the rejected type is matched.
        form.expect_data_schema_error("'not a valid type'")
        form.expect_name(name)
        assert form.get_data_schema() == json.loads(BAD_TYPE_SCHEMA_TEXT)
        assert schemas_named(api, name) == [], "A rejected schema should not be created"

    @pytest.mark.behavioral
    def test_create_invalid_config_context_schema_non_object(self, auth_page, base_url, api, schema_names_to_delete):
        """A schema that is not an object with properties is rejected with Nautobot's own message."""
        name = unique_name()
        schema_names_to_delete.append(name)

        form = ConfigContextSchemaFormPage(auth_page, base_url)
        form.navigate()
        form.fill(name=name, data_schema=NON_OBJECT_SCHEMA_TEXT)
        form.submit()

        form.expect_on_add_form()
        form.expect_data_schema_error(NON_OBJECT_ERROR, exact=True)
        form.expect_name(name)
        assert schemas_named(api, name) == [], "A rejected schema should not be created"

    # -------------------------------------------------------------------------
    # Replaces Selenium test_validation_tab
    # -------------------------------------------------------------------------

    @pytest.mark.behavioral
    def test_validation_tab_reports_valid_children(self, auth_page, base_url, created_schema_validation_tree):
        """Each panel lists its one bound object, and that object passes."""
        tree = created_schema_validation_tree
        detail = ConfigContextSchemaDetailPage(auth_page, base_url)
        detail.navigate_to_validation_tab(tree["schema"]["id"])

        for panel, row_name in validation_rows(tree).items():
            detail.expect_validation_rows(panel, [row_name])
            detail.expect_validation_passed(panel, row_name)

    @pytest.mark.behavioral
    def test_validation_tab_reports_schema_drift(
        self, auth_page, base_url, update_object, created_schema_validation_tree
    ):
        """After the schema changes a property's type, each bound object fails with the type error."""
        tree = created_schema_validation_tree
        update_object("extras/config-context-schemas/", tree["schema"]["id"], data_schema=RETYPED_SCHEMA)

        detail = ConfigContextSchemaDetailPage(auth_page, base_url)
        detail.navigate_to_validation_tab(tree["schema"]["id"])

        for panel, row_name in validation_rows(tree).items():
            detail.expect_validation_rows(panel, [row_name])
            detail.expect_validation_failed(panel, row_name, RETYPED_ERROR)

    @pytest.mark.behavioral
    def test_validation_tab_reports_mixed_state(
        self, auth_page, base_url, update_object, created_schema_validation_tree
    ):
        """After only the device's data is fixed to match the changed schema, the device passes and the others still fail."""
        tree = created_schema_validation_tree
        update_object("extras/config-context-schemas/", tree["schema"]["id"], data_schema=RETYPED_SCHEMA)
        update_object("dcim/devices/", tree["device"]["id"], local_config_context_data=RETYPED_COMPLIANT_DATA)

        detail = ConfigContextSchemaDetailPage(auth_page, base_url)
        detail.navigate_to_validation_tab(tree["schema"]["id"])

        rows = validation_rows(tree)
        for panel, row_name in rows.items():
            detail.expect_validation_rows(panel, [row_name])
        detail.expect_validation_passed("Devices", rows["Devices"])
        detail.expect_validation_failed("Config Contexts", rows["Config Contexts"], RETYPED_ERROR)
        detail.expect_validation_failed("Virtual Machines", rows["Virtual Machines"], RETYPED_ERROR)

    @pytest.mark.behavioral
    def test_validation_tab_reports_missing_required_property(
        self, auth_page, base_url, update_object, created_schema_validation_tree
    ):
        """After the schema requires a property the bound objects lack, each one fails with the required-property error."""
        tree = created_schema_validation_tree
        update_object("extras/config-context-schemas/", tree["schema"]["id"], data_schema=REQUIRED_SCHEMA)

        detail = ConfigContextSchemaDetailPage(auth_page, base_url)
        detail.navigate_to_validation_tab(tree["schema"]["id"])

        for panel, row_name in validation_rows(tree).items():
            detail.expect_validation_rows(panel, [row_name])
            detail.expect_validation_failed(panel, row_name, REQUIRED_ERROR)
