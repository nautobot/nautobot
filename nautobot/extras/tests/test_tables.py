from django.apps import apps
from django.test import RequestFactory
from django.urls import reverse
from django.utils.html import escape
from jsonschema import Draft7Validator

from nautobot.core.testing import TestCase
from nautobot.extras.models import ConfigContext, ConfigContextSchema, GitRepository, Job, JobResult
from nautobot.extras.tables import ConfigContextSchemaValidationStateColumn, JobResultTable, JobTable


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


class JobTableTestCase(TestCase):
    def test_name_links_to_run_with_object_permission(self):
        """A Job table uses object-scoped run permissions for both row and name destinations."""
        jobs = list(Job.objects.filter(installed=True)[:2])
        self.assertEqual(len(jobs), 2)
        Job.objects.filter(pk__in=[job.pk for job in jobs]).update(enabled=True)
        for job in jobs:
            job.refresh_from_db()
        self.add_permissions("extras.run_job", constraints={"pk": str(jobs[0].pk)})
        table = JobTable(jobs, user=self.user)
        rows = list(table.rows)
        run_url = reverse("extras:job_run", kwargs={"pk": jobs[0].pk})
        self.assertEqual(table.get_row_url(jobs[0]), run_url)
        self.assertIn(f'href="{run_url}"', rows[0].get_cell("name"))
        self.assertIsNone(table.get_row_url(jobs[1]))
        self.assertNotIn("href=", rows[1].get_cell("name"))
        self.assertEqual(rows[1].attrs["aria-disabled"], "true")

    def test_disabled_and_uninstalled_jobs_have_no_run_link(self):
        self.add_permissions("extras.run_job")
        job = Job.objects.get(job_class_name="TestPassJob")
        for enabled, installed in ((False, True), (True, False)):
            with self.subTest(enabled=enabled, installed=installed):
                job.enabled = enabled
                job.installed = installed
                table = JobTable([job], user=self.user)
                self.assertIsNone(table.get_row_url(job))
                self.assertNotIn("href=", next(iter(table.rows)).get_cell("name"))

    def test_render_uses_request_user_when_no_user_was_passed(self):
        """Normal table rendering obtains its permissions from the rendering request."""
        self.add_permissions("extras.run_job")
        job = Job.objects.get(job_class_name="TestPassJob")
        job.enabled = job.installed = True
        table = JobTable([job])
        request = RequestFactory().get("/")
        request.user = self.user
        table.before_render(request)
        self.assertEqual(table.get_row_url(job), reverse("extras:job_run", kwargs={"pk": job.pk}))

    def test_source_version_column_abbreviates_commit_hash(self):
        """Git commit hashes render abbreviated to 7 characters with the full hash as hover text."""
        repo = GitRepository(
            name="Source Version Table Test Repo",
            slug="source_version_table_test_repo",
            remote_url="http://localhost/git.git",
            current_head="0123456789abcdef0123456789abcdef01234567",
        )
        repo.validated_save()
        job = Job.objects.get(job_class_name="TestPassJob")
        job.module_name = f"{repo.slug}.jobs.my_job"
        job.save()
        table = JobTable(Job.objects.filter(pk=job.pk))

        cell = next(iter(table.rows)).get_cell("source_version")

        self.assertEqual(cell, '<span title="0123456789abcdef0123456789abcdef01234567">0123456</span>')

    def test_source_version_column_renders_app_version_unmodified(self):
        """Non-hash version strings (e.g. App versions) render as-is."""
        job = Job.objects.get(job_class_name="ExampleJob")
        table = JobTable(Job.objects.filter(pk=job.pk))

        cell = next(iter(table.rows)).get_cell("source_version")

        self.assertEqual(cell, apps.get_app_config("example_app").version)

    def test_source_version_column_renders_placeholder_when_unknown(self):
        """JOBS_ROOT jobs have no version information and render the empty placeholder."""
        job = Job.objects.get(job_class_name="TestPassJob")
        table = JobTable(Job.objects.filter(pk=job.pk))

        cell = next(iter(table.rows)).get_cell("source_version")

        self.assertEqual(cell, table.default)


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
