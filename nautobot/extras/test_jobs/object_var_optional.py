from nautobot.core.celery import register_jobs
from nautobot.dcim.models import Location
from nautobot.extras.jobs import get_task_logger, Job, ObjectVar

logger = get_task_logger(__name__)


class TestOptionalObjectVar(Job):
    location = ObjectVar(
        description="Location (optional)",
        model=Location,
        required=False,
    )

    def run(self, location=None):  # pylint: disable=arguments-differ
        logger.info("The Location if any that the user provided.", extra={"object": location})
        return "Nice Location (or not)!"


register_jobs(TestOptionalObjectVar)
