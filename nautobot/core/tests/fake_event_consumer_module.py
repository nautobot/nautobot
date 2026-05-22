"""Fixture module used by ``test_event_consumers.RunEventConsumersCommandTest``.

Defines a concrete ``EventConsumerJob`` subclass that the management command can
``import_string`` at startup. The class is intentionally **not** passed to
``register_jobs(...)`` — we only need it importable; the corresponding ``Job`` model row
is created directly by the test in ``_create_fake_job``.
"""

# pylint: disable=no-name-in-module
from nautobot.core.events import EventConsumerJob

# pylint: enable=no-name-in-module


class FakeEventConsumerJob(EventConsumerJob):
    """Test-only ``EventConsumerJob`` subclass; never actually executed by Celery in tests."""

    class Meta:
        hidden = True
        has_sensitive_variables = False
        name = "Fake Event Consumer Job"
        description = "Fixture for run_event_consumers tests."

    def process_event(self, *, topic, payload, headers, source_consumer):
        return {"topic": topic, "payload": payload}
