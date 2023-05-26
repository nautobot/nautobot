from django.conf import settings

from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, BooleanVar, IntegerVar, StringVar, ObjectVar, get_task_logger
from nautobot.extras.models import Role


logger = get_task_logger(__name__)


class APITestJob(Job):
    class Meta:
        name = "Job for API Tests"
        has_sensitive_variables = False
        task_queues = [settings.CELERY_TASK_DEFAULT_QUEUE, "nonexistent"]

    var1 = StringVar()
    var2 = IntegerVar(required=True)  # explicitly stated, though required=True is the default in any case
    var3 = BooleanVar()
    var4 = ObjectVar(model=Role)

    def run(self, var1, var2, var3, var4):
        logger.debug(var1)
        logger.info(var2)
        logger.warning(var3)
        logger.error(var4)

        return "Job complete"


register_jobs(APITestJob)
