from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, ObjectVar, get_task_logger
from nautobot.dcim.models import Location


logger = get_task_logger(__name__)


class TestOptionalObjectVar(Job):
    location = ObjectVar(
        description="Location (optional)",
        model=Location,
        required=False,
    )

    def run(self, location=None):
        logger.info("The Location if any that the user provided.", extra={"object": location})
        return "Nice Location (or not)!"


register_jobs(TestOptionalObjectVar)
