from io import StringIO
import json
import re
import subprocess
from unittest import mock

from django.conf import settings
from django.test import override_settings
from django.utils import timezone

from nautobot.core.testing import CelerySubprocessTestCase, TestCase
from nautobot.extras.choices import JobConsoleEntryOutputTypeChoices, JobResultStatusChoices
from nautobot.extras.jobs_console_log import (
    JobConsoleLogExecutor,
    JobConsoleLogSubprocessError,
    store_job_output_line,
    StreamReader,
)
from nautobot.extras.models.jobs import Job, JobConsoleEntry, JobResult


class StoreJobOutputLineTestCase(TestCase):
    """Test the basic storage function."""

    def setUp(self):
        job = Job.objects.first()
        self.job_result = JobResult.objects.create(
            job_model=job, name=job.class_path, date_done=timezone.now(), status=JobResultStatusChoices.STATUS_STARTED
        )

    def test_stores_stdout_line(self):
        """Test storing stdout line to database."""
        self.assertFalse(JobConsoleEntry.objects.filter(job_result=self.job_result).exists())
        store_job_output_line(
            job_result=self.job_result,
            data="Test output line\n",
            output_type="stdout",
        )

        self.assertTrue(JobConsoleEntry.objects.filter(job_result=self.job_result).exists())
        job_console_log = JobConsoleEntry.objects.get(job_result=self.job_result)
        self.assertEqual(job_console_log.job_result_id, self.job_result.id)
        self.assertEqual(job_console_log.output_type, "stdout")
        self.assertEqual(job_console_log.text, "Test output line\n")

    def test_stores_stderr_line(self):
        """Test storing stderr line to database."""

        self.assertFalse(JobConsoleEntry.objects.filter(job_result=self.job_result).exists())

        store_job_output_line(
            job_result=self.job_result,
            data="Error message\n",
            output_type="stderr",
        )

        self.assertTrue(JobConsoleEntry.objects.filter(job_result=self.job_result).exists())
        job_console_log = JobConsoleEntry.objects.get(job_result=self.job_result)
        self.assertEqual(job_console_log.job_result_id, self.job_result.id)
        self.assertEqual(job_console_log.output_type, "stderr")
        self.assertEqual(job_console_log.text, "Error message\n")

    def test_empty_data_is_not_store_in_database(self):
        """Test not storing empty data in database."""
        self.assertFalse(JobConsoleEntry.objects.filter(job_result=self.job_result).exists())
        store_job_output_line(
            job_result=self.job_result,
            data="",
            output_type="output",
        )
        self.assertFalse(JobConsoleEntry.objects.filter(job_result=self.job_result).exists())

    @override_settings(
        SANITIZER_PATTERNS=((re.compile(r"(secret is )\S+"), r"\1{replacement}"),),
    )
    def test_output_line_is_sanitized_before_storing(self):
        """Test that sensitive data is sanitized."""
        store_job_output_line(
            job_result=self.job_result,
            data="The secret is supersecret123\n",
            output_type="stdout",
        )

        job_console_log = JobConsoleEntry.objects.get(job_result=self.job_result)
        self.assertEqual(job_console_log.text, "The secret is (redacted)\n")
        self.assertNotIn("supersecret123", job_console_log.text)


class StreamReaderTestCase(TestCase):
    """Test StreamReader class."""

    def setUp(self):
        job = Job.objects.first()
        self.job_result = JobResult.objects.create(
            job_model=job,
            name=job.class_path,
            date_done=timezone.now(),
            status=JobResultStatusChoices.STATUS_STARTED,
        )

    def test_reads_and_stores_lines(self):
        """Test that StreamReader reads lines and calls store function."""
        stored_lines = []

        def mock_store(data):
            stored_lines.append({"data": data})

        fake_stream = StringIO("line 1\nline 2\nline 3\n")

        reader = StreamReader("stdout", mock_store)
        reader.read_and_store(fake_stream)

        self.assertEqual(len(stored_lines), 3)
        self.assertEqual(stored_lines[0]["data"], "line 1\n")
        self.assertEqual(stored_lines[1]["data"], "line 2\n")
        self.assertEqual(stored_lines[2]["data"], "line 3\n")

    def test_queue_receives_lines(self):
        """Test that queue receives lines for real-time consumption."""

        def mock_store(data):
            pass

        fake_stream = StringIO("line 1\nline 2\n")
        reader = StreamReader("stdout", mock_store)
        reader.read_and_store(fake_stream)

        lines = list(reader.drain_queue())
        self.assertEqual(lines, ["line 1\n", "line 2\n"])


class MockStream:
    """Mock file-like stream for testing."""

    def __init__(self, content):
        self.lines = [line + "\n" for line in content.split("\n") if line]
        self.index = 0
        self.closed = False

    def readline(self):
        if self.index >= len(self.lines):
            return ""
        line = self.lines[self.index]
        self.index += 1
        return line

    def close(self):
        self.closed = True


class JobConsoleLogExecutorTestCase(CelerySubprocessTestCase):
    """Test JobConsoleLogExecutor class."""

    def setUp(self):
        super().setUp()
        job = Job.objects.get_for_class_path("pass_job.TestPassJob")
        job.enabled = True
        job.save()
        self.job_result = JobResult.objects.create(
            job_model=job,
            name=job.class_path,
            date_done=timezone.now(),
            user=self.user,
            status=JobResultStatusChoices.STATUS_STARTED,
            celery_kwargs={
                "nautobot_job_console_log": True,
                "nautobot_job_user_id": self.user.id,
                "nautobot_job_job_model_id": job.id,
                "nautobot_job_profile": False,
                "queue": "default",
            },
        )
        self.add_permissions("extras.run_job")

    @mock.patch("nautobot.extras.jobs_console_log.subprocess.Popen", wraps=subprocess.Popen)
    def test_executor_runs_subprocess(self, mock_popen):
        """Test that executor runs subprocess with correct command."""
        # Create mock streams
        stdout_stream = MockStream("")
        stderr_stream = MockStream("")

        # Mock process
        process = mock.MagicMock()
        process.stdout = stdout_stream
        process.stderr = stderr_stream

        job_kwargs = {}  # it has to be empty, because TestPassJob expected kwargs empty
        executor = JobConsoleLogExecutor(job_result_pk=self.job_result.pk, job_kwargs=job_kwargs)

        with self.celery_subprocess_env():
            result = executor.execute()
        mock_popen.assert_called_once_with(
            [
                "nautobot-server",
                "execute_job_result",
                f"{self.job_result.pk}",
                f"--config={settings.SETTINGS_PATH}",
                "--data",
                json.dumps(job_kwargs),
            ],
            stdout=mock.ANY,
            stderr=mock.ANY,
            universal_newlines=True,
            bufsize=1,
        )
        self.assertTrue(result)
        self.job_result.refresh_from_db()
        self.assertTrue(self.job_result.result)

    @mock.patch("nautobot.extras.jobs_console_log.subprocess.Popen")
    def test_executor_stores_output_to_database(self, mock_popen):
        """Test that executor stores output lines to database."""
        # Create mock streams
        stdout_stream = MockStream("stdout line 1\nstdout line 2")
        stderr_stream = MockStream("stderr line 1")

        # Mock process
        process = mock.MagicMock()
        process.stdout = stdout_stream
        process.stderr = stderr_stream
        process.wait.return_value = 0
        process.poll.return_value = 0

        # Mock context manager
        mock_popen.return_value.__enter__.return_value = process

        executor = JobConsoleLogExecutor(self.job_result.pk)
        executor.execute()

        stdout_lines = JobConsoleEntry.objects.filter(job_result_id=self.job_result.pk, output_type="stdout").order_by(
            "timestamp"
        )

        stderr_lines = JobConsoleEntry.objects.filter(job_result_id=self.job_result.pk, output_type="stderr").order_by(
            "timestamp"
        )

        self.assertEqual(stdout_lines.count(), 2)
        self.assertEqual(stderr_lines.count(), 1)
        self.assertEqual(stdout_lines[0].text, "stdout line 1\n")
        self.assertEqual(stdout_lines[1].text, "stdout line 2\n")
        self.assertEqual(stderr_lines[0].text, "stderr line 1\n")

    @mock.patch("nautobot.extras.jobs_console_log.subprocess.Popen")
    def test_executor_handle_failure_raises_exception(self, mock_popen):
        """Test that executor raises exception with last stderr line on failure."""
        # Create mock streams
        stdout_stream = MockStream("")
        stderr_stream = MockStream("stderr line 1\nstderr line 2\n")

        # Mock process
        process = mock.MagicMock()
        process.stdout = stdout_stream
        process.stderr = stderr_stream
        process.wait.return_value = 1
        process.poll.return_value = 1

        # Mock context manager
        mock_popen.return_value.__enter__.return_value = process

        executor = JobConsoleLogExecutor(self.job_result.pk)

        with self.assertRaises(JobConsoleLogSubprocessError) as exc:
            executor.execute()

        self.assertEqual(str(exc.exception), "stderr line 2")

        self.assertEqual(
            str(exc.exception),
            JobConsoleEntry.objects.filter(
                job_result=self.job_result,
                output_type=JobConsoleEntryOutputTypeChoices.TYPE_STDERR,
            )
            .values_list("text", flat=True)
            .last()
            .rstrip(),
        )

    @mock.patch("nautobot.extras.jobs_console_log.JobConsoleEntry.objects.filter")
    @mock.patch("nautobot.extras.jobs_console_log.subprocess.Popen")
    def test_executor_handle_failure_raises_exception_with_default_ms(self, mock_popen, mock_filter):
        """Test that executor raises exception with default msg when no stderr DB entry exists."""
        # Create mock streams
        stdout_stream = MockStream("")
        stderr_stream = MockStream("stderr line 1\nstderr line 2\n")

        # Mock process
        process = mock.MagicMock()
        process.stdout = stdout_stream
        process.stderr = stderr_stream
        process.wait.return_value = 1
        process.poll.return_value = 1

        # Mock context manager
        mock_popen.return_value.__enter__.return_value = process

        mock_filter.return_value.values_list.return_value = []

        executor = JobConsoleLogExecutor(self.job_result.pk)

        with self.assertRaises(JobConsoleLogSubprocessError) as exc:
            executor.execute()

        self.assertEqual(exc.exception.args[0], "Job console log subprocess failed")
