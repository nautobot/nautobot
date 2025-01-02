from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import get_task_logger, Job, MultiObjectVar, ObjectVar
from nautobot.extras.models import Role

logger = get_task_logger(__name__)
name = "Object Vars"


class TestObjectVars(Job):
    class Meta:
        description = "Validate Objects"

    role = ObjectVar(model=Role)
    roles = MultiObjectVar(model=Role)

    def run(self, role, roles):  # pylint: disable=arguments-differ
        logger.info("Role: %s", role)
        logger.warning("Roles: %s", roles)

        logger.info("Job didn't crash!")

        return "Nice Roles!"


register_jobs(TestObjectVars)
