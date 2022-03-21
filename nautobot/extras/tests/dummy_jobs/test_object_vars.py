from nautobot.dcim.models import DeviceRole
from nautobot.extras.jobs import Job, ObjectVar, MultiObjectVar

name = "Object Vars"


class TestObjectVars(Job):
    class Meta:
        description = "Validate Objects"

    role = ObjectVar(model=DeviceRole)
    roles = MultiObjectVar(model=DeviceRole)

    def run(self, data, commit):
        role = data["role"]
        roles = data["roles"]

        # store the object data for later
        self.job_result.data["object_vars"] = {
            "role": str(role.pk),
            "roles": [str(r) for r in roles.values_list("pk", flat=True)],
        }

        self.log_info(f"Role: {role}")
        self.log_warning(f"Roles: {roles}")

        self.log_success(message="Job didn't crash!")

        return "Nice Roles!"
