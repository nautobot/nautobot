from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, ObjectVar, get_task_logger
from nautobot.dcim.models import Location


logger = get_task_logger(__name__)


class TestRequiredObjectVar(Job):
    location = ObjectVar(
        description="Location (required)",
        model=Location,
        required=True,
    )

    def run(self, location):
        logger.info("The Location that the user provided.", extra={"object": location})
        return "Nice Location!"


register_jobs(TestRequiredObjectVar)
