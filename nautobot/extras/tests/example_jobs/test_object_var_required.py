from nautobot.extras.jobs import Job, ObjectVar
from nautobot.dcim.models import Region


class TestRequiredObjectVar(Job):
    region = ObjectVar(
        description="Region (required)",
        model=Region,
        required=True,
    )

    def run(self, data, commit):
        self.log_info(obj=data["region"], message="The Region that the user provided.")
        return "Nice Region!"
