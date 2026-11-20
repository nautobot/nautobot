from rest_framework.exceptions import ParseError

from nautobot.core.api.parsers import normalize_form_data_custom_fields
from nautobot.core.testing import TestCase


class NormalizeFormDataCustomFieldsTest(TestCase):
    def test_json_encoded_custom_fields(self):
        data = {
            "manufacturer": "uuid",
            "model": "test",
            "custom_fields": '{"example": "hello"}',
        }
        result = normalize_form_data_custom_fields(data)
        self.assertEqual(result["custom_fields"], {"example": "hello"})
        self.assertEqual(set(result.keys()), {"manufacturer", "model", "custom_fields"})

    def test_cf_prefix_keys(self):
        data = {"manufacturer": "uuid", "cf_example": "hello", "cf_other": ""}
        result = normalize_form_data_custom_fields(data)
        self.assertEqual(result["custom_fields"], {"example": "hello", "other": None})
        self.assertNotIn("cf_example", result)

    def test_dotted_and_bracket_keys(self):
        data = {
            "custom_fields.example": "dotted",
            "custom_fields[bracketed]": "bracket",
        }
        result = normalize_form_data_custom_fields(data)
        self.assertEqual(result["custom_fields"], {"example": "dotted", "bracketed": "bracket"})

    def test_invalid_json_raises_parse_error(self):
        with self.assertRaises(ParseError):
            normalize_form_data_custom_fields({"custom_fields": "not-json"})

    def test_non_object_json_raises_parse_error(self):
        with self.assertRaises(ParseError):
            normalize_form_data_custom_fields({"custom_fields": '["a"]'})
