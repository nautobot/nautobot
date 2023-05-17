import logging

from celery import current_task


class NautobotLogHandler(logging.NullHandler):
    """Custom logging handler to log messages to JobLogEntry database entries."""

    def handle(self, record):
        if current_task is None:
            return

        from nautobot.extras.models.jobs import JobLogEntry, JobResult

        if not JobResult.objects.filter(id=record.task_id).exists():
            return

        JobLogEntry.objects.create(
            job_result_id=record.task_id, log_level=record.levelname.lower(), message=record.message
        )
