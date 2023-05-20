import logging

from celery import current_task


class NautobotDatabaseHandler(logging.Handler):
    """Custom logging handler to log messages to JobLogEntry database entries."""

    def emit(self, record):
        if current_task is None:
            return

        from nautobot.extras.models.jobs import JobResult

        try:
            self.format(record)

            if record.task_id == "???":
                return
            job_result = JobResult.objects.filter(id=record.task_id)
            if not job_result.exists():
                return
            job_result.first().log(
                message=record.message,
                level_choice=record.levelname.lower(),
                obj=getattr(record, "object", None),
                grouping=getattr(record, "grouping", record.funcName),
            )
        except Exception:
            self.handleError(record)
