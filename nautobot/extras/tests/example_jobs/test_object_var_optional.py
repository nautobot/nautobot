from nautobot.extras.jobs import Job, ObjectVar
from nautobot.dcim.models import Location


class TestOptionalObjectVar(Job):
    location = ObjectVar(
        description="Location (optional)",
        model=Location,
        required=False,
    )

    def run(self, data, commit):
        self.log_info(obj=data["location"], message="The Location if any that the user provided.")
        return "Nice Location (or not)!"
