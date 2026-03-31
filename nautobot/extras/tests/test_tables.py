from django.utils.html import escape
from jsonschema import Draft7Validator

from nautobot.core.testing import TestCase
from nautobot.extras.models import ConfigContext, ConfigContextSchema
from nautobot.extras.tables import ConfigContextSchemaValidationStateColumn


class ConfigContextSchemaValidationStateColumnTestCase(TestCase):
    def test_render_invalid_data_shows_validation_error(self):
        schema = ConfigContextSchema.objects.create(
            name="Schema 1",
            data_schema={"type": "object", "properties": {"foo": {"type": "integer"}}},
        )
        config_context = ConfigContext.objects.create(
            name="Config Context 1",
            weight=100,
            data={"foo": "bar"},
            config_context_schema=schema,
        )
        column = ConfigContextSchemaValidationStateColumn(Draft7Validator(schema.data_schema), "data")

        rendered = column.render(record=config_context)

        self.assertIn("mdi-close-thick", rendered)
        self.assertIn("text-danger", rendered)
        self.assertIn(escape("'bar' is not of type 'integer'"), rendered)
