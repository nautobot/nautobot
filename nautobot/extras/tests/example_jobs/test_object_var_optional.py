from nautobot.extras.jobs import Job, ObjectVar
from nautobot.dcim.models import Region


class TestOptionalObjectVar(Job):
    region = ObjectVar(
        description="Region (optional)",
        model=Region,
        required=False,
    )

    def run(self, data, commit):
        self.log_info(obj=data["region"], message="The Region if any that the user provided.")
        return "Nice Region (or not)!"
