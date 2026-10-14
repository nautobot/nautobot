"""The conditions editor on the Webhook add and edit forms."""

import pytest

from nautobot.extras.tests.integration.pages.webhook_form_page import WebhookFormPage
from nautobot.playwright.helpers import unique_name

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
    def test_a_filled_row_writes_its_condition_to_the_json_field(self, auth_page, base_url):
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate()

        _fill_planned_to_active(webhook_form)

        assert webhook_form.get_conditions() == [PLANNED_TO_ACTIVE]

    @pytest.mark.behavioral
    def test_a_condition_saved_through_the_form_reaches_the_api(self, auth_page, base_url, api):
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate()
        webhook_form.fill_name_and_payload_url(unique_name(), "https://example.com/webhook")
        _fill_planned_to_active(webhook_form)

        pk = webhook_form.save()

        try:
            response = api.get(f"/api/extras/webhooks/{pk}/")
            assert response.ok, f"GET webhook {pk} returned {response.status}: {response.text()}"
            assert response.json()["conditions"] == [PLANNED_TO_ACTIVE]
        finally:
            api.delete(f"/api/extras/webhooks/{pk}/")

    @pytest.mark.behavioral
    def test_a_stored_condition_is_drawn_as_a_row_in_the_edit_form(self, auth_page, base_url, create_webhook):
        webhook = create_webhook([PLANNED_TO_ACTIVE])
        webhook_form = WebhookFormPage(auth_page, base_url)

        webhook_form.navigate_to_edit(webhook["id"])

        assert webhook_form.get_condition_row_selections(0) == {
            "negate": "when",
            "type": "field_transition",
            "field": "status",
            "field_subfield": "name",
            "from": "Planned",
            "to": "Active",
        }

    @pytest.mark.behavioral
    def test_removing_a_row_drops_its_condition_and_announces_the_new_count(self, auth_page, base_url, create_webhook):
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
        webhook = create_webhook(THREE_USER_CONDITIONS)
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate_to_edit(webhook["id"])
        webhook_form.remove_condition(1)

        webhook_form.add_condition()

        assert webhook_form.get_condition_row_indexes() == [0, 2, 3]
        webhook_form.expect_announced_count("3 conditions")
