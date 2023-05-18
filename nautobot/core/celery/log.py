import logging

from celery import current_task


class NautobotLogHandler(logging.NullHandler):
    """Custom logging handler to log messages to JobLogEntry database entries."""

    def handle(self, record):
        if current_task is None:
            return

        from nautobot.extras.models.jobs import JobResult

        job_result = JobResult.objects.filter(id=record.task_id)
        if not job_result.exists():
            return

        job_result.first().log(
            message=record.message,
            level_choice=record.levelname.lower(),
            obj=getattr(record, "object", None),
            grouping=getattr(record, "grouping", record.funcName),
        )
