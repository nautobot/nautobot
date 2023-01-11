from django.conf import settings

from nautobot.extras.jobs import Job, BooleanVar, IntegerVar, StringVar, ObjectVar
from nautobot.extras.models import Role


class APITestJob(Job):
    class Meta:
        name = "Job for API Tests"
        has_sensitive_variables = False
        task_queues = [settings.CELERY_TASK_DEFAULT_QUEUE, "nonexistent"]

    var1 = StringVar()
    var2 = IntegerVar(required=True)  # explicitly stated, though required=True is the default in any case
    var3 = BooleanVar()
    var4 = ObjectVar(model=Role)

    def run(self, data, commit=True):
        self.log_debug(message=data["var1"])
        self.log_info(message=data["var2"])
        self.log_success(message=data["var3"])
        self.log_warning(message=data["var4"])

        return "Job complete"
