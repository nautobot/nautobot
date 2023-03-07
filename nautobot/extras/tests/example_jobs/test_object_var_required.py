from nautobot.extras.jobs import Job, ObjectVar
from nautobot.dcim.models import Location


class TestRequiredObjectVar(Job):
    location = ObjectVar(
        description="Location (required)",
        model=Location,
        required=True,
    )

    def run(self, data, commit):
        self.log_info(obj=data["location"], message="The Location that the user provided.")
        return "Nice Location!"
