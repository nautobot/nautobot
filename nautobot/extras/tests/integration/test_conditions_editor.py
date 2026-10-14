"""The conditions editor on the Webhook form: the rows and the JSON field they write."""

import pytest

from nautobot.extras.tests.integration.pages.webhook_form_page import WebhookFormPage
from nautobot.playwright.helpers import unique_name

PLANNED_TO_ACTIVE = {
    "negate": False,
    "preset": "field_transition",
    "type": "preset",
    "values": {"field": "status.name", "from": "Planned", "to": "Active"},
}


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
    def test_a_stored_condition_is_drawn_as_a_row_in_the_edit_form(self, auth_page, base_url, created_webhook):
        webhook_form = WebhookFormPage(auth_page, base_url)

        webhook_form.navigate_to_edit(created_webhook["id"])

        assert webhook_form.get_condition_row_selections(0) == {
            "negate": "when",
            "type": "field_transition",
            "field": "status",
            "field_subfield": "name",
            "from": "Planned",
            "to": "Active",
        }
