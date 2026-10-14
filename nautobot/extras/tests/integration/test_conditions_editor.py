"""The conditions editor on the Webhook form: the rows and the JSON field they write."""

import pytest

from nautobot.extras.tests.integration.pages.webhook_form_page import WebhookFormPage


class ConditionsEditorTestCase:
    """The conditions editor, driven through its rows."""

    @pytest.mark.behavioral
    def test_a_filled_row_writes_its_condition_to_the_json_field(self, auth_page, base_url):
        webhook_form = WebhookFormPage(auth_page, base_url)
        webhook_form.navigate()

        webhook_form.pick_content_type("DCIM | device")
        webhook_form.pick_condition_type(0, "Field transition")
        # The sub-field is left as the editor chooses it, `name`, which is first among those of a status.
        webhook_form.pick_condition_field(0, "Status")
        webhook_form.pick_condition_value(0, "from", "Planned")
        webhook_form.pick_condition_value(0, "to", "Active")

        assert webhook_form.get_conditions() == [
            {
                "negate": False,
                "preset": "field_transition",
                "type": "preset",
                "values": {"field": "status.name", "from": "Planned", "to": "Active"},
            }
        ]
