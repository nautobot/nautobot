"""Tests for the Custom Field add and edit forms, and for custom field values on the Device edit form and detail view."""

import pytest

from nautobot.dcim.tests.integration.pages.device_create_page import DeviceCreatePage
from nautobot.dcim.tests.integration.pages.device_detail_page import DeviceDetailPage
from nautobot.extras.tests.integration.pages.custom_field_detail_page import CustomFieldDetailPage
from nautobot.extras.tests.integration.pages.custom_field_form_page import CustomFieldFormPage
from nautobot.extras.tests.integration.pages.custom_fields_page import CustomFieldsPage
from nautobot.playwright.helpers import unique_name

DEVICE_CONTENT_TYPE = "DCIM | device"
# The add form shows this many blank choice rows. The edit form shows them after the saved choices.
EXTRA_CHOICE_ROWS = 5
# The weight that a new choice row starts with.
DEFAULT_CHOICE_WEIGHT = 100

# Which parts of the form customfield_form.js shows for each type: the Validation Rules card, its
# minimum, maximum and regex fields, and the Custom Field Choices card. Checked in this order.
VISIBLE_PARTS_BY_TYPE = {
    "text": {"validation_rules": True, "minimum": True, "maximum": True, "regex": True, "choices": False},
    "integer": {"validation_rules": True, "minimum": True, "maximum": True, "regex": False, "choices": False},
    "boolean": {"validation_rules": False, "minimum": False, "maximum": False, "regex": False, "choices": False},
    "date": {"validation_rules": False, "minimum": False, "maximum": False, "regex": False, "choices": False},
    "datetime": {"validation_rules": False, "minimum": False, "maximum": False, "regex": False, "choices": False},
    "url": {"validation_rules": True, "minimum": True, "maximum": True, "regex": True, "choices": False},
    "select": {"validation_rules": True, "minimum": True, "maximum": True, "regex": True, "choices": True},
    "multi-select": {"validation_rules": True, "minimum": True, "maximum": True, "regex": True, "choices": True},
    "json": {"validation_rules": True, "minimum": True, "maximum": True, "regex": True, "choices": False},
    "markdown": {"validation_rules": True, "minimum": True, "maximum": True, "regex": True, "choices": False},
}

LENGTH_HELP_TEXT = ("Minimum length of the value.", "Maximum length of the value.")
NUMERIC_HELP_TEXT = ("Minimum numeric value.", "Maximum numeric value.")
# The minimum and maximum help text for each type that shows those fields, checked in this order.
HELP_TEXT_BY_TYPE = {
    "text": LENGTH_HELP_TEXT,
    "integer": NUMERIC_HELP_TEXT,
    "url": LENGTH_HELP_TEXT,
    "select": LENGTH_HELP_TEXT,
    "multi-select": LENGTH_HELP_TEXT,
    "json": LENGTH_HELP_TEXT,
    "markdown": LENGTH_HELP_TEXT,
}


def open_add_form(page, base_url):
    """Open the add form from the Custom Fields list's Add button and return its page object."""
    custom_fields = CustomFieldsPage(page, base_url)
    custom_fields.navigate()
    custom_fields.click_add()
    return CustomFieldFormPage(page, base_url)


def start_device_custom_field(page, base_url, create_object, label, field_type):
    """Open the add form and fill in *label*, *field_type* and the Device content type.

    The field that the test then saves through the form is deleted after the test.
    """
    create_object.track("extras/custom-fields/", label=label)
    form = open_add_form(page, base_url)
    form.pick_content_type(DEVICE_CONTENT_TYPE)
    form.select_type(field_type)
    form.fill_label(label)
    return form


def submit_new_custom_field(page, base_url, form, label):
    """Submit the add form, check that it opened the new field's detail view, and return that page object."""
    form.submit()
    detail = CustomFieldDetailPage(page, base_url)
    detail.expect_flash_message(f"Created custom field {label}")
    detail.expect_heading(label)
    detail.expect_edit_button()
    return detail


def get_custom_field(api, label):
    """Return the API record of the one custom field labelled *label*."""
    response = api.get("/api/extras/custom-fields/", params={"label": label})
    assert response.ok, f"GET custom fields labelled {label} returned {response.status}: {response.text()}"
    results = response.json()["results"]
    assert len(results) == 1, f"Expected one custom field labelled {label}, found {len(results)}."
    return results[0]


def get_choices(api, custom_field):
    """Return the saved choices of *custom_field* (an API record) as a {value: weight} dict."""
    response = api.get("/api/extras/custom-field-choices/", params={"custom_field": custom_field["key"]})
    assert response.ok, f"GET choices of {custom_field['key']} returned {response.status}: {response.text()}"
    return {choice["value"]: choice["weight"] for choice in response.json()["results"]}


def get_device_custom_fields(api, device):
    """Return the `custom_fields` dict of *device* (an API record), read again from the API."""
    response = api.get(f"/api/dcim/devices/{device['id']}/")
    assert response.ok, f"GET device {device['id']} returned {response.status}: {response.text()}"
    return response.json()["custom_fields"]


def open_device_edit_form(page, base_url, device):
    """Open *device*'s edit form from its detail view's Edit button and return the form's page object."""
    detail = DeviceDetailPage(page, base_url)
    detail.navigate(device["id"])
    detail.click_edit()
    return DeviceCreatePage(page, base_url)


class CustomFieldTestCase:
    """The Custom Field add and edit forms, including their choice rows and type-dependent fields, and custom field values on devices."""

    # -------------------------------------------------------------------------
    # Select and multi-select fields, and their choice rows
    # -------------------------------------------------------------------------

    @pytest.mark.behavioral
    def test_create_type_select_with_choices(self, auth_page, base_url, api, create_object):
        """A select field and a multi-select field created with two choices each show both choices on their detail view."""
        choices = ["choice1", "choice2"]
        for field_type in ("select", "multi-select"):
            label = unique_name()
            form = start_device_custom_field(auth_page, base_url, create_object, label, field_type)
            for index, value in enumerate(choices):
                form.choices.fill(index, value)

            detail = submit_new_custom_field(auth_page, base_url, form, label)

            detail.expect_choices(choices)
            custom_field = get_custom_field(api, label)
            assert custom_field["type"]["value"] == field_type
            assert set(get_choices(api, custom_field)) == set(choices)

    @pytest.mark.behavioral
    def test_create_type_select_without_choices(self, auth_page, base_url, api, create_object):
        """A select field and a multi-select field can be created with no choices."""
        for field_type in ("select", "multi-select"):
            label = unique_name()
            form = start_device_custom_field(auth_page, base_url, create_object, label, field_type)

            submit_new_custom_field(auth_page, base_url, form, label)

            custom_field = get_custom_field(api, label)
            assert custom_field["type"]["value"] == field_type
            assert get_choices(api, custom_field) == {}

    @pytest.mark.behavioral
    def test_create_type_select_with_choices_adding_dynamic_row(self, auth_page, base_url, api, create_object):
        """Clicking "Add another" adds a sixth choice row with the default weight, and its choice is saved with the others."""
        label = unique_name()
        form = start_device_custom_field(auth_page, base_url, create_object, label, "select")
        form.choices.fill(0, "choice1")
        form.choices.fill(1, "choice2")
        form.choices.expect_row_count(EXTRA_CHOICE_ROWS)

        new_row = form.choices.add_row()

        assert new_row == EXTRA_CHOICE_ROWS
        form.choices.expect_row_count(EXTRA_CHOICE_ROWS + 1)
        form.choices.expect_row(new_row, "", weight=DEFAULT_CHOICE_WEIGHT)
        form.choices.fill(new_row, "choice3")

        detail = submit_new_custom_field(auth_page, base_url, form, label)

        detail.expect_choices(["choice1", "choice2", "choice3"])
        assert set(get_choices(api, get_custom_field(api, label))) == {"choice1", "choice2", "choice3"}

    @pytest.mark.behavioral
    def test_update_type_select_with_choices_editing_existing_choice(
        self, auth_page, base_url, api, create_device_custom_field
    ):
        """Clearing a saved choice fails validation. Changing it to a new value replaces the choice."""
        custom_field = create_device_custom_field("select", choices=["replace_me"])
        label = custom_field["label"]
        detail = CustomFieldDetailPage(auth_page, base_url)
        detail.navigate(custom_field["id"])
        detail_url = detail.current_url()
        detail.click_edit()
        form = CustomFieldFormPage(auth_page, base_url)
        form.expect_url_contains("/edit/")

        # A saved choice cannot be blank.
        form.choices.fill(0, "")
        form.choices.expect_row(0, "")
        form.submit()
        form.expect_flash_message(f"{label} failed validation")
        form.choices.expect_row_error(0, "This field is required.")
        assert get_choices(api, custom_field) == {"replace_me": DEFAULT_CHOICE_WEIGHT}

        form.choices.fill(0, "new_choice")
        form.submit()

        detail.expect_url_contains(detail_url)
        detail.expect_flash_message(f"Modified custom field {label}")
        detail.expect_choices(["new_choice"])
        detail.expect_no_choice("replace_me")
        assert set(get_choices(api, custom_field)) == {"new_choice"}

    # TODO(NAUTOBOT-XXXX): remove this marker when the bug is fixed. Deleting a saved choice's row hides the
    # row but sets TOTAL_FORMS to the number of rows still shown (jquery.formset.js). The hidden row keeps its
    # index, so the last row, the one added here, falls outside TOTAL_FORMS and its choice is not saved.
    @pytest.mark.xfail(
        strict=True, reason="NAUTOBOT-XXXX: a row added before a saved choice's row is deleted is not saved"
    )
    @pytest.mark.behavioral
    def test_update_type_select_create_delete_choices(self, auth_page, base_url, api, create_device_custom_field):
        """Deleting the saved choice's row and filling a newly added row in one edit replaces the choice."""
        custom_field = create_device_custom_field("select", choices=["delete_me"])
        label = custom_field["label"]
        detail = CustomFieldDetailPage(auth_page, base_url)
        detail.navigate(custom_field["id"])
        detail_url = detail.current_url()
        detail.click_edit()
        form = CustomFieldFormPage(auth_page, base_url)

        new_row = form.choices.add_row()
        form.choices.delete_row(0)
        form.choices.fill(new_row, "new_choice")
        form.submit()

        detail.expect_url_contains(detail_url)
        detail.expect_flash_message(f"Modified custom field {label}")
        detail.expect_choices(["new_choice"])
        detail.expect_no_choice("delete_me")
        assert set(get_choices(api, custom_field)) == {"new_choice"}

    # -------------------------------------------------------------------------
    # Custom field values on a device
    # -------------------------------------------------------------------------

    @pytest.mark.behavioral
    def test_custom_field_advanced_ui(self, auth_page, base_url, api, created_device, create_device_custom_field):
        """The field's label and value show on the device's main tab while `advanced_ui` is False, and only on its Advanced tab once it is True."""
        value = "This is some testing text"
        device = created_device["device"]
        custom_field = create_device_custom_field("text")
        response = api.patch(f"/api/dcim/devices/{device['id']}/", data={"custom_fields": {custom_field["key"]: value}})
        assert response.ok, f"PATCH device {device['id']} returned {response.status}: {response.text()}"
        # The API discards a value whose key is missing from its cached list of the model's custom fields,
        # so check that the value was saved before looking for it in the UI.
        assert response.json()["custom_fields"].get(custom_field["key"]) == value

        detail = DeviceDetailPage(auth_page, base_url)
        detail.navigate(device["id"])
        for text in (custom_field["label"], value):
            detail.expect_tab_to_contain("main", text)
            detail.expect_tab_not_to_contain("advanced", text)

        response = api.patch(f"/api/extras/custom-fields/{custom_field['id']}/", data={"advanced_ui": True})
        assert response.ok, f"PATCH custom field {custom_field['id']} returned {response.status}: {response.text()}"

        detail.navigate(device["id"])
        detail.open_tab("advanced")
        for text in (custom_field["label"], value):
            detail.expect_tab_not_to_contain("main", text)
            detail.expect_tab_to_contain("advanced", text)

    @pytest.mark.behavioral
    def test_json_type_with_valid_json(self, auth_page, base_url, api, created_device, create_device_custom_field):
        """Valid JSON typed into a JSON field on the device edit form is saved and shown on the device's detail view."""
        device = created_device["device"]
        custom_field = create_device_custom_field("json")

        form = open_device_edit_form(auth_page, base_url, device)
        form.fill_input(f"cf_{custom_field['key']}", '{"test_json_key": "Test JSON Value"}')
        form.submit()

        detail = DeviceDetailPage(auth_page, base_url)
        detail.expect_flash_message("Modified device")
        detail.expect_heading(device["name"])
        # The value is rendered in a collapsed <pre>, so check the row's text rather than whether it is visible.
        detail.expect_panel_field("Custom Fields", custom_field["label"], "Test JSON Value")
        assert get_device_custom_fields(api, device)[custom_field["key"]] == {"test_json_key": "Test JSON Value"}

    @pytest.mark.behavioral
    def test_json_type_with_invalid_json(self, auth_page, base_url, api, created_device, create_device_custom_field):
        """Invalid JSON typed into a JSON field on the device edit form is rejected with a field error, and nothing is saved."""
        device = created_device["device"]
        custom_field = create_device_custom_field("json")
        field_name = f"cf_{custom_field['key']}"

        form = open_device_edit_form(auth_page, base_url, device)
        # The key is not quoted, so this is not valid JSON.
        form.fill_input(field_name, '{test_json_key: "Test Invalid JSON Value"}')
        form.submit()

        form.expect_url_contains("/edit/")
        form.expect_field_error(field_name, "Enter a valid JSON")
        assert get_device_custom_fields(api, device)[custom_field["key"]] is None

    @pytest.mark.behavioral
    def test_saving_object_after_its_custom_field_deleted(
        self, auth_page, base_url, api, created_device, create_device_custom_field
    ):
        """A device that has a value for a deleted custom field can still be saved, and the value is no longer shown.

        Deleting a custom field removes its key from every cached list of custom fields (see
        `invalidate_models_cache`), so the edit form no longer displays the field and saving it
        does not fail validation on the leftover value.
        """
        choice = "SelectionChoice"
        device = created_device["device"]
        custom_field = create_device_custom_field("select", choices=[choice])

        form = open_device_edit_form(auth_page, base_url, device)
        form.pick_choice(f"cf_{custom_field['key']}", choice)
        form.submit()
        detail = DeviceDetailPage(auth_page, base_url)
        detail.expect_flash_message("Modified device")
        detail.expect_tab_to_contain("main", choice)
        assert get_device_custom_fields(api, device)[custom_field["key"]] == choice

        custom_field_detail = CustomFieldDetailPage(auth_page, base_url)
        custom_field_detail.navigate(custom_field["id"])
        custom_field_detail.delete()
        custom_field_detail.expect_flash_message(f"Deleted custom field {custom_field['label']}")

        form = open_device_edit_form(auth_page, base_url, device)
        form.submit()

        detail.expect_flash_message("Modified device")
        detail.expect_heading(device["name"])
        detail.expect_tab_not_to_contain("main", choice)
        assert custom_field["key"] not in get_device_custom_fields(api, device)

    # -------------------------------------------------------------------------
    # Type-dependent fields on the add form
    # -------------------------------------------------------------------------

    def test_type_controls_relevant_field_visibility(self, auth_page, base_url):
        """Choosing each type shows only the validation fields and choice rows that apply to that type."""
        form = open_add_form(auth_page, base_url)

        for field_type, visible in VISIBLE_PARTS_BY_TYPE.items():
            form.select_type(field_type)
            form.expect_validation_rules_card(visible["validation_rules"])
            for name in ("minimum", "maximum", "regex"):
                form.expect_validation_field(name, visible[name])
            form.expect_choices_card(visible["choices"])

    def test_type_controls_min_max_help_text(self, auth_page, base_url):
        """The minimum and maximum help text describes a numeric value for integers and a length for the other types."""
        form = open_add_form(auth_page, base_url)

        for field_type, (minimum, maximum) in HELP_TEXT_BY_TYPE.items():
            form.select_type(field_type)
            form.expect_validation_help_text(minimum, maximum)

    @pytest.mark.behavioral
    def test_submit_ignores_hidden_choice_and_validation_values(self, auth_page, base_url, api, create_object):
        """Choices and validation rules typed in before switching to a type that hides them are not saved."""
        label = unique_name()
        form = start_device_custom_field(auth_page, base_url, create_object, label, "select")
        form.choices.fill(0, "do_not_save", weight=123)
        form.select_type("text")
        form.fill_validation(minimum=7, maximum=9, regex="^do_not_save$")
        form.select_type("date")

        submit_new_custom_field(auth_page, base_url, form, label)

        custom_field = get_custom_field(api, label)
        assert custom_field["type"]["value"] == "date"
        assert get_choices(api, custom_field) == {}
        assert custom_field["validation_minimum"] is None
        assert custom_field["validation_maximum"] is None
        assert custom_field["validation_regex"] == ""

    @pytest.mark.behavioral
    def test_submit_ignores_hidden_regex_value(self, auth_page, base_url, api, create_object):
        """Switching from text to integer keeps the minimum and maximum, which integers use, and does not save the hidden regex."""
        label = unique_name()
        form = start_device_custom_field(auth_page, base_url, create_object, label, "text")
        form.fill_validation(minimum=2, maximum=10, regex="^ignore_me$")
        form.select_type("integer")

        submit_new_custom_field(auth_page, base_url, form, label)

        custom_field = get_custom_field(api, label)
        assert custom_field["type"]["value"] == "integer"
        assert custom_field["validation_minimum"] == 2
        assert custom_field["validation_maximum"] == 10
        assert custom_field["validation_regex"] == ""

    @pytest.mark.behavioral
    def test_toggle_back_preserves_choice_values(self, auth_page, base_url, api, create_object):
        """A choice typed in, hidden by switching to date, and shown again by switching back to select is still saved."""
        label = unique_name()
        form = start_device_custom_field(auth_page, base_url, create_object, label, "select")
        form.choices.fill(0, "keep_me", weight=123)
        form.select_type("date")
        form.select_type("select")

        form.choices.expect_row(0, "keep_me", weight=123)
        submit_new_custom_field(auth_page, base_url, form, label)

        custom_field = get_custom_field(api, label)
        assert custom_field["type"]["value"] == "select"
        assert get_choices(api, custom_field) == {"keep_me": 123}

    @pytest.mark.behavioral
    def test_toggle_back_preserves_validation_values(self, auth_page, base_url, api, create_object):
        """Validation rules typed in, hidden by switching to integer, and shown again by switching back to text are still saved."""
        label = unique_name()
        form = start_device_custom_field(auth_page, base_url, create_object, label, "text")
        form.fill_validation(minimum=1, maximum=22, regex="^keep_me$")
        form.select_type("integer")
        form.select_type("text")

        form.expect_input_value("validation_minimum", "1")
        form.expect_input_value("validation_maximum", "22")
        form.expect_input_value("validation_regex", "^keep_me$")
        submit_new_custom_field(auth_page, base_url, form, label)

        custom_field = get_custom_field(api, label)
        assert custom_field["type"]["value"] == "text"
        assert custom_field["validation_minimum"] == 1
        assert custom_field["validation_maximum"] == 22
        assert custom_field["validation_regex"] == "^keep_me$"
