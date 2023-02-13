import time

from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger

from nautobot.core.celery import app
from nautobot.extras.jobs import BaseJob
from nautobot.core.celery.task import NautobotJobTask


celery_logger = get_task_logger(__name__)


class BaseJobTask(BaseJob, NautobotJobTask):
    """Merge Celery Task and BaseJob."""


class NapJob(BaseJobTask):
    name = "nautobot.extras.job_tasks.NapJob"

    class Meta:
        soft_time_limit = 1
        time_limit = 5

    def run(self, *args, **kwargs):
        from nautobot.extras.choices import LogLevelChoices
        try:
            time.sleep(30)
            self.request.job_result.log("Nap complete.", logger=celery_logger, level_choice=LogLevelChoices.LOG_INFO)
        except SoftTimeLimitExceeded:
            self.request.job_result.log("Time's up! About to crash.", logger=celery_logger, level_choice=LogLevelChoices.LOG_WARNING)
            time.sleep(30)


app.register_task(NapJob)
