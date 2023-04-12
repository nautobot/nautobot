from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, ObjectVar, MultiObjectVar
from nautobot.extras.models import Role

name = "Object Vars"


class TestObjectVars(Job):
    class Meta:
        description = "Validate Objects"

    role = ObjectVar(model=Role)
    roles = MultiObjectVar(model=Role)

    def run(self, role, roles):
        self.log_info(f"Role: {role}")
        self.log_warning(f"Roles: {roles}")

        self.log_success(message="Job didn't crash!")

        return "Nice Roles!"


register_jobs(TestObjectVars)
