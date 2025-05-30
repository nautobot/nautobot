from nautobot.core.celery import register_jobs
from nautobot.dcim.models import Location
from nautobot.extras.jobs import get_task_logger, Job, ObjectVar

logger = get_task_logger(__name__)


class TestRequiredObjectVar(Job):
    location = ObjectVar(
        description="Location (required)",
        model=Location,
        required=True,
    )

    def run(self, location):  # pylint: disable=arguments-differ
        logger.info("The Location that the user provided.", extra={"object": location})
        return "Nice Location!"


register_jobs(TestRequiredObjectVar)
