import logging

from celery import current_task
from django.core.exceptions import ValidationError


class NautobotDatabaseHandler(logging.Handler):
    """Custom logging handler to log messages to JobLogEntry database entries."""

    def emit(self, record):
        if current_task is None:
            return

        from nautobot.extras.models.jobs import JobResult

        try:
            self.format(record)

            try:
                job_result = JobResult.objects.get(id=record.task_id)
            except (ValidationError, JobResult.DoesNotExist):
                # Both of these cases are very rare
                # ValidationError - because the task_id might not a valid UUID
                # JobResult.DoesNotExist - because we might not have a JobResult with that ID
                return

            # Skip recording the log entry if it has been marked as such
            if getattr(record, "skip_db_logging", False):
                return

            job_result.log(
                message=record.message,
                level_choice=record.levelname.lower(),
                obj=getattr(record, "object", None),
                grouping=getattr(record, "grouping", record.funcName),
            )
        except Exception:
            self.handleError(record)
