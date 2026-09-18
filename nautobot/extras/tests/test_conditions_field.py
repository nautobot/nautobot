"""Tests for `ConditionsField` and the mixin that puts it on a model."""

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, tag

from nautobot.core.testing import TestCase
from nautobot.extras.conditions.presets import register_builtin_condition_presets
from nautobot.extras.models import JobHook, Webhook
from nautobot.extras.models.fields import ConditionsField
from nautobot.extras.models.mixins import ConditionsMixin

EXPRESSION = {"type": "expression", "source": "data.mtu > 9000", "negate": False}
PRESET = {
    "type": "preset",
    "preset": "field_compare",
    "values": {"field": "mtu", "operator": "gt", "value": 9000},
    "negate": False,
}
BAD_ROW = {"type": "preset", "preset": "no_such_preset"}


@tag("unit")
class FieldOnBothHooksTest(SimpleTestCase):
    """Both actions that can be narrowed by conditions carry the same field."""

    def test_both_hook_models_carry_the_field(self):
        for model in (Webhook, JobHook):
            with self.subTest(model=model.__name__):
                self.assertTrue(issubclass(model, ConditionsMixin))
                self.assertIsInstance(model._meta.get_field("conditions"), ConditionsField)

    def test_the_field_defaults_to_no_conditions(self):
        self.assertEqual(Webhook().conditions, [])
        self.assertEqual(JobHook().conditions, [])


class WebhookConditionsTestCase(TestCase):
    """The field's own behaviour, exercised through one carrier; `FieldOnBothHooksTest` covers the other."""

    def setUp(self):
        super().setUp()
        register_builtin_condition_presets()

    def webhook(self, name, **kwargs):
        return Webhook(name=name, type_create=True, payload_url="https://example.com/hooks/abc", **kwargs)


@tag("unit")
class NormalisationTest(WebhookConditionsTestCase):
    def test_every_way_of_saying_no_conditions_is_stored_as_a_list(self):
        """`clean_fields()` skips a blank field, so `pre_save()` is what keeps the column to one shape."""
        for index, value in enumerate((None, "", {}, (), [])):
            with self.subTest(value=value):
                webhook = self.webhook(f"webhook-empty-{index}", conditions=value)
                webhook.save()
                webhook.refresh_from_db()
                self.assertEqual(webhook.conditions, [])

    def test_rows_survive_the_round_trip(self):
        webhook = self.webhook("webhook-rows", conditions=[PRESET, EXPRESSION])
        webhook.validated_save()
        webhook.refresh_from_db()
        self.assertEqual(webhook.conditions, [PRESET, EXPRESSION])


@tag("unit")
class ValidationTest(WebhookConditionsTestCase):
    def test_good_rows_are_accepted(self):
        self.webhook("webhook-good", conditions=[PRESET, EXPRESSION]).validated_save()

    def test_no_conditions_is_accepted(self):
        self.webhook("webhook-none", conditions=[]).validated_save()

    def test_a_bad_row_is_refused_and_the_error_names_the_field_and_the_row(self):
        with self.assertRaises(ValidationError) as caught:
            self.webhook("webhook-bad", conditions=[EXPRESSION, BAD_ROW]).validated_save()
        messages = caught.exception.message_dict["conditions"]
        self.assertEqual(len(messages), 1)
        self.assertIn("Condition 2: ", messages[0])
        self.assertIn("no_such_preset", messages[0])

    def test_a_value_that_is_not_a_list_is_refused(self):
        with self.assertRaises(ValidationError) as caught:
            self.webhook("webhook-not-a-list", conditions="data.mtu > 9000").validated_save()
        self.assertIn("must be a list of condition rows", caught.exception.message_dict["conditions"][0])
