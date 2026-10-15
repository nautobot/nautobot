"""The conditions editor on the Webhook add and edit forms."""

import re

import pytest

from nautobot.extras.tests.integration.pages.webhook_form_page import WebhookFormPage

PLANNED_TO_ACTIVE = {
    "negate": False,
    "preset": "field_transition",
    "type": "preset",
    "values": {"field": "status.name", "from": "Planned", "to": "Active"},
}

THREE_USER_CONDITIONS = [
    {"negate": False, "preset": "user_is", "type": "preset", "values": {"username": username}}
    for username in ("first", "second", "third")
]

UNREADABLE_JSON = '[{"negate": false, "preset": "user_is",'


def _fill_planned_to_active(webhook_form):
    webhook_form.pick_content_type("DCIM | device")
    webhook_form.pick_condition_type(0, "Field transition")
    # The sub-field is left as the editor chooses it, `name`, which is first among those of a status.
    webhook_form.pick_condition_field(0, "Status")
    webhook_form.pick_condition_value(0, "from", "Planned")
    webhook_form.pick_condition_value(0, "to", "Active")


class ConditionsEditorTestCase:
    """The conditions editor, driven through its rows."""

    @pytest.mark.behavioral
    def test_a_condition_saved_through_the_form_reaches_the_api(self, auth_page, base_url, api, webhook_name):
        """The row is filled through Select2 and HTMX, which the view tests never run, before the form is saved."""
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate()
        webhook_form.fill_disabled_update_webhook(webhook_name, "https://example.com/webhook")
        _fill_planned_to_active(webhook_form)

        pk = webhook_form.save()

        response = api.get(f"/api/extras/webhooks/{pk}/")
        assert response.ok, f"GET webhook {pk} returned {response.status}: {response.text()}"
        assert response.json()["conditions"] == [PLANNED_TO_ACTIVE]

    @pytest.mark.behavioral
    def test_a_stored_condition_is_drawn_as_a_row_in_the_edit_form(self, auth_page, base_url, create_webhook):
        """Select2 is set up on rows HTMX swaps in, so it has to show the stored values, not only hold them."""
        webhook = create_webhook([PLANNED_TO_ACTIVE])
        webhook_form = WebhookFormPage(auth_page, base_url)

        webhook_form.navigate_to_edit(webhook["id"])

        webhook_form.expect_condition_row_to_show(
            0,
            {
                "negate": "When",
                "type": "Field transition",
                "field": "Status",
                "field_subfield": "Name",
                "from": "Planned",
                "to": "Active",
            },
        )

    @pytest.mark.behavioral
    def test_removing_a_row_drops_its_condition_and_announces_the_new_count(self, auth_page, base_url, create_webhook):
        """A row is removed in the browser with no request, so the script alone rewrites the JSON field and count."""
        webhook = create_webhook(THREE_USER_CONDITIONS)
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate_to_edit(webhook["id"])

        webhook_form.remove_condition(1)

        assert [condition["values"]["username"] for condition in webhook_form.get_conditions()] == ["first", "third"]
        webhook_form.expect_announced_count("2 conditions")

    @pytest.mark.behavioral
    def test_a_row_added_after_a_removal_takes_the_index_past_the_highest_and_is_counted(
        self, auth_page, base_url, create_webhook
    ):
        """An index prefixes every control of its row, so one freed by a removal is never handed out again."""
        webhook = create_webhook(THREE_USER_CONDITIONS)
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate_to_edit(webhook["id"])
        webhook_form.remove_condition(1)

        webhook_form.add_condition()

        assert webhook_form.get_condition_row_indexes() == [0, 2, 3]
        webhook_form.expect_announced_count("3 conditions")

    @pytest.mark.behavioral
    def test_conditions_typed_on_the_json_tab_are_drawn_as_rows_on_the_form_tab(self, auth_page, base_url):
        """Only the browser sends what was typed, and only once Bootstrap shows the Form tab."""
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate()
        webhook_form.show_json_tab()
        webhook_form.fill_conditions(THREE_USER_CONDITIONS)

        webhook_form.show_form_tab()

        assert webhook_form.get_condition_row_indexes() == [0, 1, 2]
        usernames = [webhook_form.get_condition_row_inputs(index)["username"] for index in (0, 1, 2)]
        assert usernames == ["first", "second", "third"]

    @pytest.mark.behavioral
    def test_json_that_cannot_be_read_shows_the_message_and_is_kept_when_a_row_is_added(self, auth_page, base_url):
        """Adding a row writes the field from the rows, and with no rows to read the typed text would become `[]`."""
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate()
        webhook_form.show_json_tab()
        webhook_form.fill_conditions_text(UNREADABLE_JSON)
        webhook_form.show_form_tab()

        webhook_form.expect_unreadable_message()
        webhook_form.expect_announced_count("Conditions could not be read.")

        webhook_form.add_condition()

        webhook_form.expect_conditions_text(UNREADABLE_JSON)

    @pytest.mark.behavioral
    def test_a_condition_on_a_deleted_custom_field_is_left_unchanged_by_the_edit_form(
        self, auth_page, base_url, api, created_custom_field, create_webhook
    ):
        """The field select shows `—`, and writing the rows back while they are drawn would store it empty."""
        condition = {
            "negate": False,
            "preset": "field_changed",
            "type": "preset",
            "values": {"field": f"custom_fields.{created_custom_field['key']}"},
        }
        webhook = create_webhook([condition])
        deleted = api.delete(f"/api/extras/custom-fields/{created_custom_field['id']}/")
        assert deleted.ok, f"DELETE custom field returned {deleted.status}: {deleted.text()}"
        webhook_form = WebhookFormPage(auth_page, base_url)

        webhook_form.navigate_to_edit(webhook["id"])

        webhook_form.expect_condition_row_to_show(0, {"type": "Field change"})
        webhook_form.expect_condition_row_to_show_nothing_in(0, "field")
        assert webhook_form.get_conditions() == [condition]

    @pytest.mark.behavioral
    def test_choosing_another_field_clears_the_values_chosen_for_the_old_one(self, auth_page, base_url, create_webhook):
        """The server clears them only when told the field changed, which the browser says in `HX-Trigger-Name`."""
        webhook = create_webhook([PLANNED_TO_ACTIVE])
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate_to_edit(webhook["id"])

        webhook_form.pick_condition_field(0, "Role")

        webhook_form.expect_condition_row_to_show_nothing_in(0, "from")
        webhook_form.expect_condition_row_to_show_nothing_in(0, "to")
        assert webhook_form.get_conditions()[0]["values"] == {"field": "role.name", "from": "", "to": ""}

    @pytest.mark.behavioral
    def test_a_refused_save_shows_the_error_beside_the_control_at_fault(self, auth_page, base_url, webhook_name):
        """The page comes back without rows, and HTMX fetches them with `?validate=1` to place each error."""
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate()
        webhook_form.fill_disabled_update_webhook(webhook_name, "https://example.com/webhook")
        webhook_form.pick_content_type("DCIM | device")
        webhook_form.pick_condition_type(0, "Field comparison")
        webhook_form.pick_condition_field(0, "Status")

        webhook_form.save_expecting_refusal()

        webhook_form.expect_condition_error(0, "operator", "Parameter `operator` is required.")

    @pytest.mark.behavioral
    def test_choosing_not_when_writes_the_negation(self, auth_page, base_url, create_webhook):
        """Select2 sets the choice through jQuery, so the field is written only because the editor raises `input`."""
        webhook = create_webhook([PLANNED_TO_ACTIVE])
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate_to_edit(webhook["id"])

        webhook_form.pick_condition_negation(0, "Not When")

        assert webhook_form.get_conditions() == [{**PLANNED_TO_ACTIVE, "negate": True}]

    @pytest.mark.behavioral
    def test_the_field_select_opens_once_an_object_type_is_chosen(self, auth_page, base_url):
        """Choosing an object type draws every row again, which is what offers that type's fields."""
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate()
        webhook_form.pick_condition_type(0, "Field change")
        webhook_form.expect_condition_select_enabled(0, "field", enabled=False)

        webhook_form.pick_content_type("DCIM | device")

        webhook_form.expect_condition_select_enabled(0, "field", enabled=True)
        webhook_form.expect_condition_row_to_show(0, {"type": "Field change"})

    @pytest.mark.behavioral
    def test_a_date_is_picked_from_the_calendar_of_a_row_swapped_in(self, auth_page, base_url):
        """The row arrives as plain HTML, so its calendar works only because the editor sets up flatpickr on it."""
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate()
        webhook_form.pick_content_type("DCIM | device")
        webhook_form.pick_condition_type(0, "Field comparison")
        webhook_form.pick_condition_field(0, "Status")
        webhook_form.pick_condition_subfield(0, "Created")
        webhook_form.pick_condition_operator(0, "> (greater than)")

        webhook_form.pick_condition_day(0, "value", 15)

        values = webhook_form.get_conditions()[0]["values"]
        assert values["field"] == "status.created"
        # The calendar opens on the current month, so only the day is known.
        assert re.fullmatch(r"\d{4}-\d{2}-15", values["value"]), f"Picked {values['value']!r}, not the 15th"
