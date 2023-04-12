from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, ObjectVar
from nautobot.dcim.models import Location


class TestRequiredObjectVar(Job):
    location = ObjectVar(
        description="Location (required)",
        model=Location,
        required=True,
    )

    def run(self, location):
        self.log_info(obj=location, message="The Location that the user provided.")
        return "Nice Location!"


register_jobs(TestRequiredObjectVar)
