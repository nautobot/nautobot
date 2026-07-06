from django.utils.html import escape
from jsonschema import Draft7Validator

from nautobot.core.testing import TestCase
from nautobot.extras.models import ConfigContext, ConfigContextSchema, JobResult
from nautobot.extras.tables import ConfigContextSchemaValidationStateColumn, JobResultTable


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

    def test_render_without_real_validator_shows_no_schema_available(self):
        config_context = ConfigContext.objects.create(
            name="Config Context 1",
            weight=100,
            data={"foo": "bar"},
        )
        column = ConfigContextSchemaValidationStateColumn(None, "data")

        rendered = column.render(record=config_context)

        self.assertIn("mdi-close-thick", rendered)
        self.assertIn("text-danger", rendered)
        self.assertIn("No schema available", rendered)


class JobResultTableTestCase(TestCase):
    def test_queue_name_column_renders_queue_from_celery_kwargs(self):
        """The Queue Name column reads the queue from a JobResult's celery_kwargs."""
        job_result = JobResult.objects.create(
            name="queued.TestQueuedJob",
            celery_kwargs={"queue": "test-queue-name"},
        )
        table = JobResultTable(JobResult.objects.filter(pk=job_result.pk))

        cell = next(iter(table.rows)).get_cell("queue_name")

        self.assertEqual(cell, "test-queue-name")

    def test_queue_name_column_renders_placeholder_without_queue(self):
        """The Queue Name column renders the empty placeholder when no queue is set."""
        job_result = JobResult.objects.create(name="no_queue.TestNoQueueJob")
        table = JobResultTable(JobResult.objects.filter(pk=job_result.pk))

        cell = next(iter(table.rows)).get_cell("queue_name")

        self.assertEqual(cell, table.default)
